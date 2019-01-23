# vra-ansible

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

