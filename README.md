# vra-ansible

module: vra_request

short_description: This does various actions pertaining to VMWare VRA's REST API

version_added: "0.0.1"

description:
    - "This module allows a user to request for a service catalog item and alter various variables from the catalog items"

options:
<br />    VRA_server:
<br />        description:
<br />            - VRA server hostname or IP Address to request from
<br />        required: true
<br />    user:
<br />        description:
<br />        - Username of manamgement account, eg. admin
<br />        required: true
<br />    user_pass:
<br />        description:
<br />            - Password of management account, eg. pass
<br />        required: true
<br />    VRA_tenant:
<br />        description:
<br />            - tenant of VRA which the user is requesting from
<br />        required: true
<br />    catalog_item:
<br />        description:
<br />            - Service Catalog Item which is being requested
<br />        required: true (provide arbituary value if display_template_only is true)
<br />    provisioning_options:
<br />        description:
<br />            - provisioning options if catalog item is a VM provision request
<br />        required: false
<br />    options_file:   ## not ready yet
<br />        description:
<br />             - file containing catalog item request template
<br />        required: false
<br />    verify:
<br />        description:
<br />            - SSL Verify - False as default
<br />        required: false
<br />		catalog_timeout:
<br />		    description
<br />				    - Timeout to fulfil request (in numbers of 10s blocks)
<br />				required: false (default: 180 ~= 30 mins)
<br />    display_template_only:
<br />        description:
<br />            - Display Service Catalog Template - False as default
<br />        required: false
<br />    display_entitled_items_only:
<br />        description:
<br />            - Display Entitled Items - False as default
<br />        required: false
<br />extends_documentation_fragment:
<br />    - nil

<br />author:
<br />    - Eugene KY Wong (@eugenekywong)
'''

<br />EXAMPLES = '''
<br />  - name: Provision VM with 1 vCPU, 4GB memory and HDD of 100GB and 200GB specification
<br />    vra_request:
<br />      user: username
<br />      user_pass: "pass"
<br />      VRA_server: vra.server.mgmt
<br />      catalog_item: Provision VM (Reference)
<br />      provisioning_options:
<br />        - cpu: 1
<br />        - memory: 4096
<br />        - disks:   # This must match template - putting 0 will not make any changes to template.
<br />            - 100
<br />            - 200
<br />    register: vra_request_result
<br />
<br />    - name: Request catalog item with JSON options
<br />    vra_request:
<br />      user: username
<br />      user_pass: "pass"
<br />      VRA_server: vra.server.mgmt
<br />      catalog_item: Request DNS
<br />      options_file: test.txt    ## Works in progress
<br />    register: vra_request_result
