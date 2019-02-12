#!/usr/bin/python

import json
from ansible.module_utils.basic import AnsibleModule
import time

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

try:
    from pkg_resources import parse_version
    import avi.sdk
    from avi.sdk.avi_api import (ApiSession, ObjectNotFound, APIError, ApiResponse,
                             avi_timedelta, sessionDict)

    sdk_version = getattr(avi.sdk, '__version__', None)
    if ((sdk_version is None) or
            (sdk_version and
             (parse_version(sdk_version) < parse_version('17.1')))):
        # It allows the __version__ to be '' as that value is used in development builds
        raise ImportError
    HAS_AVI = True
except ImportError:
    HAS_AVI = False

RETRIES = 120
SLEEP = 5
INITIAL_SLEEP = 10

def main():
    module = AnsibleModule(
        argument_spec=dict(
            se_master_ctl_ip=dict(required=True, type='str'),
            se_master_ctl_username=dict(required=True, type='str'),
            se_master_ctl_password=dict(required=True, type='str', no_log=True),
            se_master_ctl_version=dict(required=True, type='str'),
            se_cloud_name=dict(required=True, type='str'),
            se_group_name=dict(required=True, type='str'),
            se_tenant=dict(required=True, type='str'),
            se_vmw_vm_name=dict(required=True, type='str'),
            se_vmw_mgmt_ip=dict(required=False, type='str'),
        ),
        supports_check_mode=False,
    )

    if not HAS_AVI:
        return module.fail_json(msg=(
            'Avi python API SDK (avisdk>=17.1) is not installed. '
            'For more details visit https://github.com/avinetworks/sdk.'))

    se_mgmt_ip = ''
    se_vm_name = module.params['se_vmw_vm_name']
    my_deployed_se = None

    if module.params.get('se_vmw_mgmt_ip', None):
        se_mgmt_ip = module.params['se_vmw_mgmt_ip']

    api = ApiSession.get_session(
        module.params['se_master_ctl_ip'], 
        module.params['se_master_ctl_username'], 
        password=module.params['se_master_ctl_password'], 
        tenant=module.params['se_tenant'])

    path = 'serviceengine'
    gparams = {
        'cloud_ref.name': module.params['se_cloud_name'],
        'se_group_ref.name': module.params['se_group_name']
    }

    step = 0
    time.sleep(INITIAL_SLEEP)
    while step < RETRIES:
        rsp = api.get(path, tenant=module.params['se_tenant'],
                            params=gparams, api_version=module.params['se_master_ctl_version'])
        rsp_data = rsp.json()
        for item in rsp_data['results']:
            if (item['name'] == se_vm_name or item['name'] == se_mgmt_ip) and item['se_connected']:
                my_deployed_se = item
                break
        
        if my_deployed_se != None:
            mymsg = 'Service Engine \'%s\' is deployed and is connected to the Controller %s' % (
                my_deployed_se['name'], module.params['se_master_ctl_ip'])
            return module.exit_json(changed=True, msg=(mymsg))
        time.sleep(SLEEP)
        step += 1

    return module.exit_json(msg='Could not verify SE connection to the controller!')

if __name__ == "__main__":
    main()