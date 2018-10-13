import os, sys, requests
from base64 import b64encode
from requests.utils import to_native_string

from ngw_connection_settings import NGWConnectionSettings
from ngw_connection import NGWConnection
import conf


def basic_auth_str(username, password):
    """Returns a Basic Auth string"""
    authstr = 'Basic ' + to_native_string(
        b64encode(('%s:%s' % (username, password)).encode('utf-8')).strip()
    )
    return authstr


def is_S1_render(fname):
    """checks if the filename is valid name for S1 renders ready for upload"""
    if fname[-11:] == '_render.tif' and fname[:9] == 'niersc_s1':
        return True
    else:
        return False


def create_raster_layer(file_name, parent_id, headers):
    """uploads raster, creates raster layer in directory with parent_id, creates raster style for it"""
    print('Uploading ' + file_name)
    attachment_info = ngwConnection.upload_file(file_name)
    display_name = file_name.split("/")[-1][:-11]  # cuts the "_render.tif" suffix
    payload = {
        "resource": {
            "cls": "raster_layer",
            "display_name": display_name,
            "parent": {"id": parent_id}
        },
        "raster_layer": {
            "source": attachment_info,
            "srs": {"id": 3857}
        }
    }
    r = requests.post(conf.HOST + '/api/resource/', headers=headers, json=payload)
    if r.status_code == 201:
        created_resource_id = r.json()['id']
        print('Raster layer with id %s was created' % created_resource_id)
        payload = {
            "resource": {"cls": "raster_style", "description": None, "display_name": display_name, "keyname": None,
                         "parent": {"id": created_resource_id}}}
        r = requests.post(conf.HOST + '/api/resource/', headers=headers, json=payload)  # creates raster style
    # TODO: check if it was created
    # print r
    else:
        print('Failed: %s responded %s. %s' % (conf.HOST, r.status_code, r.json()['message']))


ngwConnectionSettings = NGWConnectionSettings("test", "http://webgis.niersc.spb.ru", "aterekhov", "00aterekhov00")
ngwConnection = NGWConnection(ngwConnectionSettings)

headers = {'Accept': '*/*', 'Authorization': basic_auth_str(conf.LOGIN, conf.PASSWORD)}

# get the directories list under the 'Daily' folder
payload = {'parent': conf.ngw_resources_id}
r = requests.get(conf.HOST + '/api/resource/', headers=headers, params=payload)
if r.status_code == 200:
    dir_list = list()
    dir_id_list = list()
    for resource in r.json():
        dir_list.append(resource['resource']['display_name'])
        dir_id_list.append(resource['resource']['id'])

for fname in os.listdir(conf.sourcedir):
    if os.path.isfile(conf.sourcedir + fname) and is_S1_render(fname):
        fname = conf.sourcedir + fname  # later we need full paths only
        render_date = fname.split("_")[2].split("T")[
            0]  # this extracts the date from file name. Update it when naming conventions change
        # Checks if the directory for this date already exists in the Daily folder.
        # If so, uploads raster layer inside it.
        # Otherwise, creates a new directory for this date, then upload.
        if render_date in dir_list:
            print("%s folder already exists" % (render_date))
            ngw_date_dir_id = dir_id_list[
                dir_list.index(render_date)]  # get ID of a folder with a corresponding date to upload render in it
            create_raster_layer(fname, ngw_date_dir_id, headers)
        else:
            print("%s folder does not exist, creating" % render_date)
            payload = {"resource":
                           {"cls": "resource_group",
                            "parent": {"id": conf.ngw_resources_id},
                            "display_name": render_date,
                            "keyname": None,
                            "description": conf.ngw_resources_id}
                       }
            r = requests.post(conf.HOST + '/api/resource/', headers=headers, json=payload)
            if r.status_code == 201:
                ngw_date_dir_id = r.json()['id']
                print('Folder with id %s created' % (ngw_date_dir_id))
                dir_list.append(render_date)
                dir_id_list.append(ngw_date_dir_id)
                create_raster_layer(fname, ngw_date_dir_id, headers)
