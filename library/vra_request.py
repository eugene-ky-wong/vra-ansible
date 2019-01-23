#!/usr/bin/pytho
import traceback
import pdb

from ansible.module_utils.basic import AnsibleModule

try:
    import json
    import requests
    import ast
    import time

    from collections import namedtuple
    from requests.exceptions import ConnectionError
    HAS_LIB=True

except ImportError:
    HAS_LIB=False


ANSIBLE_METADATA = {
    'metadata_version': '0.0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: vra_request

short_description: This does various actions pertaining to VMWare VRA's REST API

version_added: "0.0.1"

description:
    - "This module allows a user to request for a service catalog item and alter various variables from the catalog items"

options:
    VRA_server:
        description:
            - VRA server hostname or IP Address to request from
        required: true
    user:
        description:
        - Username of manamgement account, eg. admin
        required: true
    user_pass:
        description:
            - Password of management account, eg. pass
        required: true
    VRA_tenant:
        description:
            - tenant of VRA which the user is requesting from
        required: true
    catalog_item:
        description:
            - Service Catalog Item which is being requested
        required: true (provide arbituary value if display_template_only is true)
    provisioning_options:
        description:
            - provisioning options if catalog item is a VM provision request
        required: false
    options_file:   ## not ready yet
        description:
             - file containing catalog item request template
        required: false
    verify:
        description:
            - SSL Verify - False as default
        required: false
    catalog_timeout:
        description
            - Timeout to fulfil request (in numbers of 10s blocks)
        required: false (default: 180 ~= 30 mins)
    display_template_only:
        description:
            - Display Service Catalog Template - False as default
        required: false
    display_entitled_items_only:
        description:
            - Display Entitled Items - False as default
        required: false
extends_documentation_fragment:
    - nil

author:
    - Eugene KY Wong (@eugenekywong)
'''

EXAMPLES = '''
  - name: Provision VM with 1 vCPU, 4GB memory and HDD of 100GB and 200GB specification
    vra_request:
      user: username
      user_pass: "pass"
      VRA_server: vra.server.mgmt
      catalog_item: Provision VM (Reference)
      provisioning_options:
        - cpu: 1
        - memory: 4096
        - disks:   # This must match template - putting 0 will not make any changes to template.
            - 100
            - 200
    register: vra_request_result

    - name: Request catalog item with JSON options
    vra_request:
      user: username
      user_pass: "pass"
      VRA_server: vra.server.mgmt
      catalog_item: Request DNS
      options_file: test.txt    ## Works in progress
    register: vra_request_result
'''

RETURN = '''
original_message:
    description: The original name param that was passed in
    type: str
message:
    description: The output message that the sample module generates
'''

from ansible.module_utils.basic import AnsibleModule


class Error(Exception):
    """Base class for other exceptions"""
    pass

class ConnectionError(Error):
    """Raised connection error to device time outs"""
    pass

class LoginLogoutError(Error):
    """Raised login to device"""
    pass

class ConnectTimeoutError(Error):
    """Base class for connection timeout"""
    pass


class VRA(object):
    """
    Class for use with VRA API.
    """

    def __init__(self, user, user_pass, VRA_server, VRA_tenant, catalog_item, provisioning_options,
        options_file, module, display_template_only, display_entitled_items_only, phase, verbose=True, verify=False,
        disable_warnings=False, timeout=30, catalog_timeout=180):
#        """
#        Init method for VRA class
#        :param user: API user name
#        :param user_pass: API user password
#        :param VRA_server: VRA server IP address or Hostname
#        :param VRA_tenant: VRA tenant
#        :param verify: Verify HTTPs certificate verification
#        :param timeout: Timeout for request response
#        """
        self.user = user
        self.user_pass = user_pass
        self.VRA_server = VRA_server
        self.VRA_tenant = VRA_tenant
        self.catalog_item = catalog_item
        self.provisioning_options = provisioning_options
        self.options_file = options_file
        self.verify = verify
        self.verbose = verbose
        self.display_template_only = display_template_only
        self.display_entitled_items_only = display_entitled_items_only
        self.disable_warnings = disable_warnings
        #self.catalog_timeout = catalog_timeout
        self.timeout = timeout
        self.module = module

        self.current_phase = ''

        if self.disable_warnings:
            requests.packages.urllib3.disable_warnings()

        self.base_url = 'https://{0}'.format(
            self.VRA_server,
        )

        self.vsession = requests.session()
        if not self.verify:
            self.vsession.verify = self.verify


        ## Login and get token
        (self.login_result, self.data, self.headers) = self.login()
        token = self.login_result['id']
        self.std_headers = {'Content-Type': 'application/json', 'Accept': 'application/json',
            'Authorization': 'Bearer {0}'.format(token)}


        ## Get Entitled Catalog Items View
        self.entitled_catalog_items_view = self.entitled_catalog_items_view()

        if display_entitled_items_only:
            return


        ## Get catalog_item_id, get_url and post_url
        self.data_eci = self.entitled_catalog_items_view['content']
        self.get_URL = None
        self.post_URL = None
        self.catalog_item_id = False
        for item in self.data_eci:
            if item.get('name') == catalog_item:
                self.catalog_item_id = item['catalogItemId']
                self.get_url = item['links'][0]['href']
                self.post_url = item['links'][1]['href']
                break
        if (not self.catalog_item_id):
            module.fail_json(msg = '{0} not found in list of entited catalog items.'.format(catalog_item))


        ## Search and get Catalog Service Template
        self.request_template = self.catalog_service_template(self.catalog_item_id, self.get_url)


        ## Check provisioning_options and apply options to template
        if len(self.provisioning_options) > 0:
            self.string=''

            for item in self.request_template['data']:
                #self.string=self.string+item+','
                if (not isinstance(self.request_template['data'][item], dict) or
						        'data' not in self.request_template['data'][item]):
                    continue

                for item2 in self.request_template['data'][item]['data']:
                #self.string=self.string+item2+':'
                    if 'cpu' in item2:
                        for prov_item in self.provisioning_options:
                            if prov_item == 'disks':
                                continue
                            self.request_template['data'][item]['data'][prov_item] = self.provisioning_options[prov_item]

                        if 'disks' in self.provisioning_options:
                            hdd_index = 0
                            no_of_disks_template = len(self.request_template['data'][item]['data']['disks'])
                            no_of_disks = len(self.provisioning_options['disks'])
                            if no_of_disks_template != no_of_disks:
                                module.fail_json(msg = '{0} found in template, while {1} disk-size change(s) requested'.format(no_of_disks_template,
                                    no_of_disks))
                            for capacity in self.provisioning_options['disks']:
                                if capacity == 0:
                                   continue
                                self.request_template['data'][item]['data']['disks'][hdd_index]['data']['capacity'] = capacity
                                hdd_index += 1

        if display_template_only:
            return


        ## Submit Catalog Item Request
        self.request_catalog_result = self.request_catalog(self.catalog_item_id, self.post_url,
            self.request_template)


        ## Wait for catalog_timeout x 10s (default: 30 mins) for job to complete
        for x in range(0, catalog_timeout):
            self.get_consumer_request_result = self.get_consumer_request(self.request_catalog_result['id'])
            self.current_phase = self.get_consumer_request_result['phase']
            if (self.current_phase in phase['phase_fail'] or
                self.current_phase in phase['phase_completed']):
                    break
            time.sleep(10)


        ## Log out and expire token
        if self.current_phase in phase['phase_completed']:
            self.logout(token)


    def gen_fail_msg(self, msg, verbose_msg):
        if self.verbose and verbose_msg:
            self.module.fail_json(msg = json.loads(verbose_msg))
            return msg + ' Error: ' + verbose_msg
        else:
            self.module.fail_json(msg = msg)
            return msg

    def login(self):
        """
        Login to VRA server
        :return: Result type tuple
        """
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        data={'username': self.user, 'password': self.user_pass, 'tenant': self.VRA_tenant}
        login_result = self._post(
            session = self.vsession, headers = headers, timeout=self.timeout, data=data,
            url='{0}/identity/api/tokens'.format(self.base_url),
        )
        return (login_result.json(), data, headers)


    def logout(self, token):
        """
        Logout from VRA server
        :return: Result type tuple
        """
        data=None
        headers = self.std_headers
        try:
            logout_result = self.delete(
                session = self.vsession, headers = headers, timeout=self.timeout, data=data,
                url='{0}/identity/api/tokens/{1}'.format(self.base_url, token),
            )
        except ConnectionError:
            self.gen_fail_msg('Could not login to {0}, check network, user credentials and tenant details.'.format(self.VRA_server),
                False)
            raise LogoutTimeoutError(fail_msg)
        except AttributeError:
            self.gen_fail_msg('API error. Check API, user credentials and tenant details.'.format(self.VRA_server),
                False)

        if logout_result.text.startswith('{"errors"'):
            fail_msg = self.gen_fail_msg('Could not log out from VRA server.', logout_result.text)
            raise Error(fail_msg)
        else:
            return (logout_result.json(), data, headers)


    def entitled_catalog_items_view(self):
        """
        Retrieve tenant's entitled catalog items
        :return: Result type dict
        """
        data = None
        headers = self.std_headers
        entitled_catalog_items_view_result = self._get(
            session = self.vsession, headers = headers, timeout=self.timeout, data=data,
            url = '{0}/catalog-service/api/consumer/entitledCatalogItemViews'.format(self.base_url),
            error = 'Could not retrieve entitled catalog items.'
        )
        return entitled_catalog_items_view_result.json()


    def catalog_service_template(self, catalog_item_id, get_url):
        """
        Retrieve tenant's catalog_service_template
        :return: Result type dict
        """
        data = None
        headers = self.std_headers
        catalog_service_template_result = self._get(
            session = self.vsession, headers = headers, timeout=self.timeout, data=data,
            url = '{0}'.format(get_url),
            error = 'Could not request for catalog item template.'
        )
        return catalog_service_template_result.json()


    def request_catalog(self, catalog_item_id, post_url, request_template):
        """
        Request Catalog Service Item
        :return: Result type dict
        """
        data = request_template
        self.data = data
        headers = self.std_headers
        request_catalog_result = self._post(
            session = self.vsession, headers = headers, timeout=self.timeout, data=data,
            url = '{0}'.format(post_url),
            error = 'Could not request catalog item.'
        )
        return request_catalog_result.json()


    def get_consumer_request(self, id):
        """
        Request Catalog Service Request Status
        :return: Result type dict
        """
        data = None
        headers = self.std_headers
        request_consumer_request_result = self._get(
            session = self.vsession, headers = headers, timeout=self.timeout, data=data,
            url = '{0}/catalog-service/api/consumer/requests/{1}'.format(self.base_url, id),
            error = 'Could not get status update.'
        )
        return request_consumer_request_result.json()

    #@staticmethod
    def _post(self, session, url, headers=None, data=None, timeout=15, error='Default error', action='post'):
        """
        Perform a HTTP post
        :param session: requests session
        :param url: url to post
        :param headers: HTTP headers
        :param data: Data payload
        :param timeout: Timeout for request response
        :return:
        """
        if headers is None:
            # add default headers for post
            headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

        try:
            _session = (session.post(url=url, headers=headers, data=json.dumps(data), timeout=timeout))

        except:
            self.gen_fail_msg('Could not connect to {0}.'.format(self.VRA_server),
                url)
            #raise ConnectionError('Connection Timed Out to {0}'.format(self.VRA_server))

        if _session.text.startswith('<') or _session.text.startswith('{"errors"'):
            self.gen_fail_msg(error, _session.text)
            #raise Error(error)

        return _session

    #@staticmethod
    def _get(self,session, url, headers=None, data=None, timeout=15, error='Default error.'):
        """
        Perform a HTTP get
        :param session: requests session
        :param url: url to post
        :param headers: HTTP headers
        :param data: Data payload
        :param timeout: Timeout for request response
        :return:
        """

        try:
            _session = (session.get(url=url, headers=headers, data=data, timeout=timeout))

        except:
            self.gen_fail_msg('Could not connect to {0}.'.format(self.VRA_server),
                url)
            #raise ConnectionError('Connection Timed Out to {0}'.format(self.VRA_server))

        if _session.text.startswith('<') or _session.text.startswith('{"errors"'):
            self.gen_fail_msg(error, url + '-' + str(data))
            raise Error(error)

        return _session


def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(
        VRA_tenant=dict(type='str', required=False, default='vsphere.local'),
        VRA_server=dict(type='str', required=True),
        catalog_item=dict(type='str', required=True),
        user=dict(type='str', required=True),
        user_pass=dict(type='str', required=True, no_log=True),
        provisioning_options=dict(type='dict', required=False),
        options_file=dict(type='str', required=False),
        display_entitled_items_only=dict(type='list', required=False),
        display_template_only=dict(type='list', required=False),
				catalog_timeout=dict(type='int', required=False, default=180),
#         do_not_fail=dict(type='bool', required=False, default=False),
        verify=dict(type='bool', required=False, default=False),
        verbose=dict(type='bool', required=False, default=False)
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # change is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False#,
        #original_message='',
        #message=''
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if not HAS_LIB:
        module.fail_json(msg="Required package(s) for this module could not be loaded.")

    verbose = module.params['verbose']
    provisioning_options = module.params['provisioning_options']

    phase={
		    'phase_fail': ['FAILED'],
			  'phase_incomplete': ['INCOMPLETE'],
		    'phase_completed': 'COMPLETED' }

    init_args = {'user': module.params['user'],
        'user_pass': module.params['user_pass'],
        'VRA_server': module.params['VRA_server'],
        'VRA_tenant': module.params['VRA_tenant'],
        'catalog_item': module.params['catalog_item'],
        'provisioning_options': module.params['provisioning_options'],
        'options_file': module.params['options_file'],
        'verify': module.params['verify'],
        'verbose': module.params['verbose'],
				'catalog_timeout': module.params['catalog_timeout'],
        'display_template_only': module.params['display_template_only'],
        'display_entitled_items_only': module.params['display_entitled_items_only'],
        'disable_warnings': 'True',
				'phase': phase,
				'module': module}


    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        return result

    # manipulate or modify the state as needed (this is going to be the
    # part where your module will do what it needs to do)
    #pdb.set_trace()

    ## Instantiation of VRA session
    session = VRA(**init_args)

    ## Return Result to Ansible User
    if session.display_entitled_items_only:
        result['entitled_catalog_items_view'] = session.entitled_catalog_items_view

    if session.display_template_only:
        result['requestTemplate'] = session.request_template

    if (not session.display_template_only and
        not session.display_entitled_items_only):

        phase_failed = ['CANCELLED', 'FAILED']
        phase_not_completed = ['IN_PROGRESS']
        if (session.current_phase in phase_not_completed or session.current_phase in phase_failed):
            fail_msg = session.get_consumer_request_result #'Service catalog request is in state {0}.'.format(session.current_phase)
            #if verbose:
            #    error_msg = session.get_consumer_request_result
            #    fail_msg = fail_msg + ' Latest request status: {0}.'.format(error_msg)
            module.fail_json(msg=fail_msg)
ls
    result['changed'] = True

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
