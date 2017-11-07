#!/usr/bin/env python
"""
Coldsnap takes a cold snapshot of a vm living on a Tintri array.

Coldsnap does the following in order:
- shuts down a vm
- takes a Tintri snapshot
- and then boots it back up
"""

import argparse
import datetime
import json
import sys
import time
import py_vmware.vmware_lib as vmware_lib
import tintri_1_1 as tintri


def get_args():
    """Get arguments from CLI."""
    parser = argparse.ArgumentParser(description='Reboot a target VM by name')

    parser.add_argument('--vcenter',
                        required=True,
                        action='store',
                        help='vCenter to connect to')

    parser.add_argument('--vcenter_port',
                        type=int,
                        default=443,
                        action='store',
                        help='vCenter Port to connect on')

    parser.add_argument('--vcenter_user',
                        required=True,
                        action='store',
                        help='Username to use for vCenter')

    parser.add_argument('--vcenter_password',
                        required=False,
                        action='store',
                        help='Password to use for vCenter')

    parser.add_argument('--vcenter_insecure',
                        required=False,
                        action='store_true',
                        help='disable ssl validation for vCenter')

    parser.add_argument('--tvmstore',
                        action='store',
                        help='Tintri Global Center to connect to')

    parser.add_argument('--tvmstore_user',
                        required=True,
                        action='store',
                        help='Username to use for TGC')

    parser.add_argument('--tvmstore_password',
                        required=False,
                        action='store',
                        help='Password to use for TGC')

    parser.add_argument('--tvmstore_consistency_type',
                        required=False,
                        action='store',
                        default='vm',
                        help='The type of Tintri snapshot to take')

    parser.add_argument('--tvmstore_snapshot_name',
                        required=True,
                        action='store',
                        help='The type of Tintri snapshot to take')

    parser.add_argument('--tvmstore_snapshot_lifetime',
                        type=int,
                        default=43800, # 1 month, -1 = no expiration
                        action='store',
                        help='minutes to keep snapshot')

    parser.add_argument('--debug_mode',
                        required=False,
                        action='store_true',
                        help='enable debug output')

    parser.add_argument('--vms',
                        nargs='+',
                        action='store',
                        help='the name of one or more vms to snapshot separated by spaces')

    args = parser.parse_args()
    return args


"""
 Tintri methods
"""

# The MIT License (MIT)
#
# Copyright (c) 2016 Tintri, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# For exhaustive messages on console, make it to True; otherwise keep it False


def print_with_prefix(prefix, out):
    print prefix + out
    return


def print_debug(out):
    args = get_args()
    if args.debug_mode:
        print_with_prefix("[DEBUG] : ", out)
    return


def print_info(out):
    print_with_prefix("[INFO] : ", out)
    return


def print_error(out):
    print_with_prefix("[ERROR] : ", out)
    return

# Take a manual snapshot.
def take_snapshot(vm_uuid, snapshot_name, consistency_type, snapshot_retention_minutes, server_name, session_id):
    snapshot_spec = {
        'typeId' : "com.tintri.api.rest.v310.dto.domain.beans.snapshot.SnapshotSpec",
        'consistency' : consistency_type,
        'retentionMinutes' : snapshot_retention_minutes,
        'snapshotName' : snapshot_name,
        'sourceVmTintriUUID' : vm_uuid }

    # The API needs a list of snapshot specifications.
    snapshot_specs = [snapshot_spec]

    ss_url = "/v310/snapshot"
    r = tintri.api_post(server_name, ss_url, snapshot_specs, session_id)
    if (r.status_code != 200):
        msg = "The HTTP response for the post invoke to the server is " + \
              server_name + "not 200, but is: " + str(r.status_code) + "."
        raise tintri.TintriApiException(msg, r.status_code, ss_url, str(snapshot_specs), r.text)

    print_debug("The JSON response of the post invoke to the server " +
                server_name + " is: " + r.text)

    # The result is a liset of snapshot UUIDs.
    snapshot_result = r.json()
    print_info(snapshot_name + ": " + snapshot_result[0])
    if snapshot_retention_minutes > -1:
        now = datetime.datetime.now()
        expiration = now + datetime.timedelta(minutes=snapshot_retention_minutes)
        print_info(snapshot_name + " will expire " + expiration.ctime())
    else:
        print_info(snapshot_name + " will be kept until manually deleted")
    return


def tintri_snapshot(args, vm):
    try:
        # Confirm the consistency type.
        if (args.tvmstore_consistency_type == "crash"):
            consistency_type = "CRASH_CONSISTENT"
        elif (args.tvmstore_consistency_type == "vm"):
            consistency_type = "VM_CONSISTENT"
        else:
            raise tintri.TintriRequestsException("tvmstore_consistency_type is not 'crash' or 'vm': " + args.tvmstore_consistency_type)

        # Get the preferred version
        r = tintri.api_version(args.tvmstore)
        json_info = r.json()

        print_info("Tintri API Version: " + json_info['preferredVersion'])

        # Login to VMstore or TGC
        session_id = tintri.api_login(args.tvmstore, args.tvmstore_user, args.tvmstore_password)

    except tintri.TintriRequestsException as tre:
        print_error(tre.__str__())
        sys.exit(-10)
    except tintri.TintriApiException as tae:
        print_error(tae.__str__())
        sys.exit(-11)


    try:
        # Create query filter to get the VM specified by the VM name.
        q_filter = {'name': vm.name}

        # Get the UUID of the specified VM
        vm_url = "/v310/vm"
        r = tintri.api_get_query(args.tvmstore, vm_url, q_filter, session_id)
        print_debug("The JSON response of the get invoke to the server " +
                    args.tvmstore + " is: " + r.text)

        vm_paginated_result = r.json()
        num_vms = int(vm_paginated_result["filteredTotal"])
        if num_vms == 0:
            raise tintri.TintriRequestsException("VM " + vm.name + " doesn't exist")

        # Get the information from the first item and hopefully the only item.
        items = vm_paginated_result["items"]
        vm = items[0]
        vm_name = vm["vmware"]["name"]
        vm_uuid = vm["uuid"]["uuid"]

        print_info(vm_name + " UUID: " + vm_uuid)

        # Get the time for the snapshot description.
        now = datetime.datetime.now()
        now_sec = datetime.datetime(now.year, now.month, now.day,
                                    now.hour, now.minute, now.second)
        snapshot_name = args.tvmstore_snapshot_name

        # Take a manual snapshot.
        take_snapshot(vm_uuid, snapshot_name, consistency_type, args.tvmstore_snapshot_lifetime, args.tvmstore, session_id)

        # All pau, log out.
        tintri.api_logout(args.tvmstore, session_id)

    except tintri.TintriRequestsException as tre:
        print_error(tre.__str__())
        tintri.api_logout(args.tvmstore, session_id)
        sys.exit(-20)
    except tintri.TintriApiException as tae:
        print_error(tae.__str__())
        tintri.api_logout(args.tvmstore, session_id)
        sys.exit(-21)



"""
VMware methods
"""


def poweroff(args, si, vm):
    print_info("powering off VM %s" % vm.name)
    if vm.runtime.powerState == vmware_lib.vim.VirtualMachinePowerState.poweredOn:
        # using time.sleep we just wait until the power off action
        # is complete. Nothing fancy here.
        try:
            if vm.guest.toolsStatus == 'toolsNotInstalled':
                print_info("VM Tools not installed, forcing power off")
                task = vm.PowerOff()
                while task.info.state not in [vmware_lib.vim.TaskInfo.State.success,
                                              vmware_lib.vim.TaskInfo.State.error]:
                    time.sleep(1)
            else:
                print_info("Initiating guest shutdown" )
                vm.ShutdownGuest()
                while vm.runtime.powerState != vmware_lib.vim.VirtualMachinePowerState.poweredOff:
                    time.sleep(1)
        except Exception as e:
            print_error(e.__str__())
            print vm.guest
            sys.exit()

        print_info("%s is powered off." % vm.name)
    else:
        print_info("%s was already powered off." % vm.name)


def poweron(args, si, vm):
    print_info("powering on VM %s" % vm.name)
    if vm.runtime.powerState == vmware_lib.vim.VirtualMachinePowerState.poweredOff:
        # using time.sleep we just wait until the power on action
        # is complete. Nothing fancy here.
        task = vm.PowerOnVM_Task()
        while task.info.state not in [vmware_lib.vim.TaskInfo.State.success,
                                      vmware_lib.vim.TaskInfo.State.error]:
            time.sleep(1)
        print_info("%s is powered on." % vm.name)
        if vm.guest.toolsStatus != 'toolsNotInstalled':
            while True:
                system_ready = vm.guest.guestOperationsReady
                system_state = vm.guest.guestState
                system_uptime = vm.summary.quickStats.uptimeSeconds
                if system_ready and system_state == 'running' and system_uptime > 30:
                    break
                time.sleep(10)
            print_info("%s is ready." % vm.name)

        if args.debug_mode:
            print_debug("Here's the output of vm.guest:")
            print vm.guest
    else:
        print_info("%s was already powered on." % vm.name)

def main():
    args = get_args()

    # connect this thing
    si = vmware_lib.connect(args.vcenter, args.vcenter_user, args.vcenter_password, args.vcenter_port, args.vcenter_insecure)
    content = si.RetrieveContent()

    for vm_name in args.vms:
        vm = vmware_lib.get_obj(content, [vmware_lib.vim.VirtualMachine], vm_name)
        poweroff(args, si, vm)
        tintri_snapshot(args, vm)
        poweron(args, si, vm)

if __name__ == "__main__":
    main()
