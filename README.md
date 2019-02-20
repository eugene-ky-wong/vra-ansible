Role Name
=========

A brief description of the role goes here.

Ansible role to integrate invoke VRA provisioning / other XAAS blueprints using Ansible.


Requirements
------------

All modules of this role require ``python2.7`` environment::

    sudo pip install ansible
    sudo pip install json
    sudo pip install requests
    sudo pip install ast
    sudo pip install time
    sudo pip install collections
    

Installation
------------
The Ansible role can be installed directly from Ansible Galaxy by running::

     ansible-galaxy install eugene_ky_wong.vra_ansible --force 

If the ``ansible-galaxy`` command-line tool is not available (usually shipped with Ansible), or you prefer to download the 
role package directly, navigate to the Ansible Galaxy `role page <https://galaxy.ansible.com/eugene_ky_wong/vra_ansible>`
and hit "Download".

Alternately, you can directly navigate to our `GitHub repository 
<https://galaxy.ansible.com/eugene_ky_wong/vra_ansible>`_.


Role Variables
--------------

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

Dependencies
------------

Python Modules:

ansible
json
requests
ast
time
collections

Example Playbook
----------------

  # Provision VM with customization
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


License
-------

BSD

Author Information
------------------

morphyme@gmail.com
https://github.com/eugene-ky-wong/vra-ansible


