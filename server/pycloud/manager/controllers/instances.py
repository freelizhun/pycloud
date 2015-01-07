import logging
import json
import urllib2
import os

# External library for creating HTTP requests.
import requests

from pylons import request
from pylons import response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons import g

from webhelpers.html.grid import Grid
from webhelpers.html import HTML
from webhelpers.html import literal

from pycloud.pycloud.pylons.lib.base import BaseController
from pycloud.manager.lib.pages import InstancesPage
from pycloud.pycloud.pylons.lib import helpers as h
from pycloud.pycloud.model import Service, ServiceVM
from pycloud.pycloud.pylons.lib.util import asjson
from pycloud.pycloud.pylons.lib.util import dumps

log = logging.getLogger(__name__)

################################################################################################################
# Controller for the ServiceVMs Instances page.
################################################################################################################
class InstancesController(BaseController):

    JSON_OK = {"STATUS" : "OK" }
    JSON_NOT_OK = { "STATUS" : "NOT OK"}
    
    ############################################################################################################
    # Shows the list of running Service VM instances.
    ############################################################################################################
    def GET_index(self):
        # Mark the active tab.
        c.servicevms_active = 'active'
        print request.environ['SCRIPT_NAME']
        svms = ServiceVM.find()

        # Setup the page to render.
        instancesPage = InstancesPage()

        instancesPage.svms = svms

        # Pass the grid and render the page.
        return instancesPage.render()
        
    ############################################################################################################
    # Opens a local VNC window to a running Service VM Instance.
    ############################################################################################################
    @asjson
    def GET_openVNC(self, id):
        try:            
            # Get the instance associated with this id.
            svm = ServiceVM.by_id(id)
            
            if not svm:
                # If we didn't get a valid id, just return an error message.
                print "Service VM id " + id + " was not found on the list of running instances."
                return self.JSON_NOT_OK
            
            # Try to start the VNC window (this will only work if done on the Cloudlet).
            svm.open_vnc(wait=False)
        except Exception as e:        
            # If there was a problem connecting through VNC, return that there was an error.
            msg = 'Error opening VNC window: ' + str(e)
            print msg
            error = self.JSON_NOT_OK
            error['error'] = msg
            return error

        
        # Everything went well.
        return self.JSON_OK

    ############################################################################################################
    # Starts a new SVM instance of the Service.
    ############################################################################################################
    @asjson
    def GET_startInstance(self, id):
        # Look for the service with this id
        service = Service.by_id(id)
        if service:
            clone_full_image = False
            if request.params.get('clone_full_image'):
                clone_full_image = True

            # Get a ServiceVM instance
            svm = service.get_vm_instance(clone_full_image=clone_full_image)
            try:
                # Start the instance, if it works, save it and return ok
                svm.start()
                svm.save()
                return {"STATUS": "OK", "_id": svm._id, "vnc_port": svm.vnc_port}
            except Exception as e:
                # If there was a problem starting the instance, return that there was an error.
                msg = 'Error starting Service VM Instance: ' + str(e)
                print msg
                error = self.JSON_NOT_OK
                error['error'] = msg
                return error
        else:
            error = self.JSON_NOT_OK
            error['message'] = 'Service {} not found.'.format(id)
            return error

    ############################################################################################################
    # Stops an existing instance.
    ############################################################################################################
    @asjson
    def GET_stopInstance(self, id):
        try:    
            # Stop an existing instance with the given ID.
            svm = ServiceVM.find_and_remove(id)
            svm.destroy()
        except Exception as e:
            # If there was a problem stopping the instance, return that there was an error.
            msg = 'Error stopping Service VM Instance: ' + str(e)
            print msg
            error = self.JSON_NOT_OK
            error['error'] = msg
            return error
        
        # Everything went well.
        return self.JSON_OK

    ############################################################################################################
    # Command to migrate a machine.
    ############################################################################################################
    @asjson
    def GET_migrateInstance(self, id):
        try:
            # Parse the body of the request as JSON into a python object.
            # First remove URL quotes added to string, and then remove trailing "=" (no idea why it is there).
            #parsedJsonString = urllib.unquote(request.body)[:-1]
            #fields = json.loads(parsedJsonString)

            # The host we are migrating to.
            remote_host = request.params.get('target', None)

            # Find the SVM.
            svm = ServiceVM.by_id(id)
            print 'VM found: ' + str(svm)

            # TODO: hardcoded port
            print 'Migrating to remote cloudlet: ' + remote_host
            remote_http_host = 'http://%s:9999' % remote_host

            # Transfer the metadata.
            print 'Starting metadata file transfer...'
            remote_url = '%s/instances/receiveMigratedSVMMetadata' % remote_http_host
            payload = json.dumps(svm)
            headers = {'content-type': 'application/json'}
            result = requests.post(remote_url, data=payload, headers=headers)
            if result.status_code != requests.codes.ok:
                raise Exception('Error transferring metadata.')
            print 'Metadata was transferred: ' + str(result)

            # We pause the VM before transferring its disk and memory state.
            print 'Pausing VM...'
            result = svm.pause()
            if result == -1:
                raise Exception("Cannot pause VM: %s", str(id))
            print 'VM paused.'

            # Transfer the disk image file.
            print 'Starting disk image file transfer...'
            disk_image_full_path = os.path.abspath(svm.vm_image.disk_image)
            remote_url = '%s/instances/receiveMigratedSVMDiskFile' % remote_http_host
            payload = {'id': id}
            files = {'disk_image_file': open(disk_image_full_path, 'rb')}
            result = requests.post(remote_url, data=payload, files=files)
            if result.status_code != requests.codes.ok:
                raise Exception('Error transferring disk image file.')
            print 'Disk image file was transferred: ' + str(result)

            # Do the memory state migration.
            remote_hostname = remote_host.split('.')[0]
            print 'Migrating through libvirt to ' + remote_hostname
            svm.migrate(remote_hostname, p2p=False)
            # TODO: if migration fails, ask remote to remove svm.

            # Notify remote cloudlet that migration finished.
            print 'Telling target cloudlet that migration has finished.'
            remote_url = '%s/instances/resumeMigratedSVM' % remote_http_host
            payload = {'id': id}
            result = requests.post(remote_url, data=payload)
            if result.status_code != requests.codes.ok:
                raise Exception('Error notifying migration end.')
            print 'Cloudlet notified: ' + str(result)

            # Remove the local VM.
            svm = ServiceVM.find_and_remove(id)
            svm.destroy()
        except:
            msg = 'Error migrating: ' + str(e)
            print msg
            import traceback
            traceback.print_exc()

            error = self.JSON_NOT_OK
            error['error'] = msg
            return error


        return self.JSON_OK

    ############################################################################################################
    # Receives information about a migrated VM.
    ############################################################################################################
    def POST_receiveMigratedSVMMetadata(self):
        # Parse the body of the request as JSON into a python object.
        json_svm = json.loads(request.body)

        # Get information about the SVM.
        print 'Obtaining metadata of SVM to be received.'
        migrated_svm = ServiceVM()
        migrated_svm._id = json_svm['_id']
        migrated_svm.vm_image = json_svm['vm_image']
        migrated_svm.port_mappings = json_svm['port_mappings']
        migrated_svm.service_port = json_svm['service_port']
        migrated_svm.port = json_svm['port']
        migrated_svm.ip_address = json_svm['ip_address']
        migrated_svm.mac_address = json_svm['mac_address']
        migrated_svm.ssh_port = json_svm['ssh_port']
        migrated_svm.vnc_port = json_svm['vnc_port']
        migrated_svm.service_id = json_svm['service_id']

        # Save to internal DB.
        migrated_svm.save()
        print 'SVM metadata stored.'

        return 'Ok!'

    ############################################################################################################
    # Receives the disk image file of a migrated SVM.
    ############################################################################################################
    def POST_receiveMigratedSVMDiskFile(self):
        # Get the id and load the metadata for this SVM.
        svm_id = request.params.get('id')
        migrated_svm = ServiceVM.by_id(svm_id)
        if not migrated_svm:
            abort(404, '404 Not Found - SVM with id %s not found' % svm_id)

        # Receive the transferred file and update its path.
        print 'Storing disk image file of SVM in migration.'
        destination_folder = os.path.join(g.cloudlet.svmInstancesFolder, svm_id)
        disk_image_object = request.params.get('disk_image_file').file
        migrated_svm.vm_image.store(destination_folder, disk_image_object)
        print 'Migrated SVM disk image file stored.'

        # Check that we have the backing file, and rebase the new file so it will point to the correct backing file.
        service = Service.by_id(migrated_svm.service_id)
        if service:
            print 'Rebasing backing file for service %s.' % migrated_svm.service_id
            backing_disk_file = service.vm_image.disk_image
            migrated_svm.vm_image.rebase_disk_image(backing_disk_file)
        else:
            # Migration will be unsuccessful since we won't have the backing file.
            print 'Service %s not found in local cloudlet.' % migrated_svm.service_id
            abort(500, '500 Server Error - Service is not installed on target cloudlet.')

        # Save to internal DB.
        migrated_svm.save()

        return 'Ok!'

    ############################################################################################################
    # Receives information about a migrated VM.
    ############################################################################################################
    def POST_resumeMigratedSVM(self):
        # Find the SVM.
        svm_id = request.params.get('id')
        migrated_svm = ServiceVM.by_id(svm_id)
        if not migrated_svm:
            print 'SVM with id %s not found.' % svm_id
            abort(404, '404 Not Found - SVM with id %s not found' % svm_id)

        # Restart the VM.
        print 'Unpausing VM...'
        result = migrated_svm.unpause()
        print 'VM running'

        # Save to internal DB.
        migrated_svm.save()

        return 'Ok!'

    ############################################################################################################
    # Returns a list of running svms.
    ############################################################################################################    
    @asjson    
    def GET_svmList(self):
        try:    
            # Get the list of running instances.
            svm_list = ServiceVM.find()
            return svm_list
        except Exception as e:
            # If there was a problem stopping the instance, return that there was an error.
            msg = 'Error getting list of instance changes: ' + str(e)
            print msg
            error = self.JSON_NOT_OK
            error['error'] = msg
            return error

############################################################################################################
# Helper function to generate a link for the service id to the service details.
############################################################################################################        
def generate_service_id_link(col_num, i, item):
    editServiceURL = h.url_for(controller='modify', action='index', id=item["service_id"])
    
    return HTML.td(HTML.a(item["service_id"], href=editServiceURL))