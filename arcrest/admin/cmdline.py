from __future__ import print_function

import argparse
import os
import sys
import time
import urlparse

from arcrest import Catalog

__all__ = ['createservice', 'manageservice', 'managesite', 'deletecache',
           'managecachetiles', 'createcacheschema',
           'convertcachestorageformat']

shared_args = argparse.ArgumentParser(add_help=False)
shared_args.add_argument('-u', '--username', 
                         required=True,
                         help='Description: Username for Server')
shared_args.add_argument('-p', '--password', 
                         required=True,
                         help='Description: Password for Server')
shared_args.add_argument('-s', '--site', 
                         required=True,
                         help='Description: URL for admin Server')
shared_args.add_argument('-t', '--token',
                         required=False,
                         action='store_true',
                         help='Description: Use token authentication '
                              '(if -t is not set, command will use HTTP auth)',
                         default=False)

class ActionNarrator(object):
    def __init__(self):
        self.action_stack = []
    def __call__(self, action):
        self.action = action
        return self
    def __enter__(self):
        self.action_stack.append(self.action)
    def __exit__(self, t, ex, tb):
        action = self.action_stack.pop()
        if (t, ex, tb) != (None, None, None):
            #import traceback
            #traceback.print_exception(t, ex, tb)
            if t is not SystemExit:
                print("Error {0}: {1}".format(action, str(ex)))
            sys.exit(1)

def get_rest_urls(admin_url):
    admin_url = urlparse.urljoin(admin_url, '/arcgis/admin/')
    rest_url = urlparse.urljoin(admin_url, '/arcgis/rest/services/')
    return (admin_url, rest_url)

def provide_narration(fn):
    def fn_():
        return fn(ActionNarrator())
    return fn_

def wait_on_tool_run(result_object, silent=False):
    message_length = 0
    while result_object.running:
        time.sleep(0.125)
        messages = getattr(result_object, 'messages', [])
        if len(messages) > message_length:
            for message_object in messages[message_length:]:
                if not silent:
                    print (message_object.description)
                    sys.stdout.flush()
            message_length = len(messages)
    if not silent:
        for message_object in messages[message_length:]:
            print (message_object.description)

createserviceargs = argparse.ArgumentParser(description='Creates a service',
                                            parents=[shared_args])
createserviceargs.add_argument('-C', '--cluster',
                               nargs='?',
                               default=None,
                               help='Name of cluster to act on')
createserviceargs.add_argument('-f', '--sdfile',
                                nargs='+',
                                metavar="FILE",
                                help='Filename of local Service Definition '
                                     'file')
createserviceargs.add_argument('-F', '--folder-name',
                               nargs='?',
                               default=None,
                               help='Folder to create service in')
createserviceargs.add_argument('-n', '--service-name',
                               nargs='?',
                               default=None,
                               help='Name of service to create')
createserviceargs._optionals.title = "arguments"

@provide_narration
def createservice(action):
    import arcrest.admin as admin
    args = createserviceargs.parse_args()
    files = args.sdfile
    admin_url, rest_url = get_rest_urls(args.site)
    with action("connecting to admin site {0}".format(admin_url)):
        site = admin.Admin(admin_url, args.username, args.password,
                           generate_token=args.token)
        assert site._json_struct.get('status', 'ok') != 'error',\
               ' '.join(site._json_struct.get('messages',
                   ['Could not connect to site.']))
    with action("connecting to REST services {0}".format(rest_url)):
        rest_site = Catalog(rest_url, args.username, args.password,
                            generate_token=args.token)
    with action("looking up Publish Tool"):
        publish_tool = (rest_site['System']
                                 ['PublishingTools']
                                 ['Publish Service Definition'])
    with action("looking up cluster"):
        cluster = site.clusters[args.cluster] if args.cluster else None
    with action("verifying service definition file exists"):
        all_files = [os.path.abspath(filename) for filename in files]
        assert all_files, "No file specified"
        for filename in all_files:
            assert os.path.exists(filename) and os.path.isfile(filename), \
                    "{0} is not a file".format(filename)
    ids = []
    publish_tool.__post__ = True
    for filename in all_files:
        with action("uploading {0}".format(filename)):
            id = site.uploads.upload(filename)['itemID']
            with action("publishing {0}".format(os.path.basename(filename))):
                result_object = publish_tool(id,
                                             site.url[
                                                 :site.url.find('?')])
                wait_on_tool_run(result_object, silent=True)

manageserviceargs = argparse.ArgumentParser(description=
                                                'Manages/modifies a service',
                                            parents=[shared_args])
manageserviceargs.add_argument('-n', '--name',
                               default=None,
                               help='Description: Service name (optional)')
manageserviceargs.add_argument('-o', '--operation',
                               default=None,
                               help="Description: Operation to perform on "
                                    "specified service. If -l or --list is "
                                    "specified, used as a status filter "
                                    "instead.",
                               choices=['status', 'start', 'stop', 'delete'])
manageserviceargs.add_argument('-l', '--list',
                               default=False,
                               action='store_true',
                               help="Description: List services on server "
                                    "(optional)")
manageserviceargs._optionals.title = "arguments"

@provide_narration
def manageservice(action):
    import arcrest.admin as admin
    args = manageserviceargs.parse_args()
    admin_url, rest_url = get_rest_urls(args.site)
    if args.list:
        with action("checking arguments"):
            assert not args.name, "name cannot be set if listing services"
        with action("connecting to admin site {0}".format(admin_url)):
            site = admin.Admin(admin_url, args.username, args.password,
                                          generate_token=args.token)
            assert site._json_struct.get('status', 'ok') != 'error',\
                   ' '.join(site._json_struct.get('messages',
                       ['Could not connect to site.']))
        with action("listing services"):
            services = site.services
            folders = services.folders
        with action("printing services"):
            status_map = {'stopped': 'stop',
                          'started': 'started'}
            servicelist = list(services.services)
            for folder in folders:
                servicelist += list(folder.services)
            for service in servicelist:
                print("{0:40} | {1}".format(
                                (service.parent.folderName+"/"
                                    if service.parent.folderName != "/"
                                    else ""
                                )+service.name,
                                service.status['realTimeState']))
    else:
        with action("checking arguments"):
            assert args.name, "Service name not specified"
        with action("connecting to admin site {0}".format(admin_url)):
            site = admin.Admin(admin_url, args.username, args.password,
                               generate_token=args.token)
            assert site._json_struct.get('status', 'ok') != 'error',\
                   ' '.join(site._json_struct.get('messages',
                       ['Could not connect to site.']))
        with action("listing services"):
            services = site.services
        with action("searching for service %s" % args.name):
            service = services[args.name]
        operation = (args.operation or '').lower()
        if operation == 'status':
            for key, item in sorted(service.status.iteritems()):
                print("{0}: {1}".format(key, item))
        elif operation == 'start':
            with action("starting service"):
                return service.start()
        elif operation == 'stop':
            with action("stopping service"):
                return service.stop()
        elif operation == 'delete':
            with action("deleting service"):
                return service.delete()

managesiteargs = argparse.ArgumentParser(description=
                                                'Manages/modifies a site',
                                            parents=[shared_args])
managesiteargs.add_argument('-A', '--add-machines',
                               nargs='+',
                               help='Machines to add to cluster')
managesiteargs.add_argument('-R', '--remove-machines',
                               nargs='+',
                               help='Machines to remove from cluster')
managesiteargs.add_argument('-l', '--list',
                               default=False,
                               action='store_true',
                               help='List machines on a site')
managesiteargs.add_argument('-lc', '--list-clusters',
                               default=False,
                               action='store_true',
                               help='List clusters on a site')
managesiteargs.add_argument('-o', '--operation',
                               nargs='?',
                               help='Description: Operation to perform on '
                                    'cluster',
                               choices=['chkstatus', 'start', 'stop'])
managesiteargs.add_argument('-c', '--cluster',
                               nargs='?',
                               default=None,
                               help='Name of cluster to act on')
managesiteargs.add_argument('-D', '--delete-cluster',
                               default=False,
                               action='store_true',
                               help='Delete cluster specified with -c')
managesiteargs.add_argument('-cr', '--create-cluster',
                               default=False,
                               action='store_true',
                               help=('Create cluster specified with -c '
                                     'if it does not exist'))
managesiteargs._optionals.title = "arguments"

@provide_narration
def managesite(action):
    import arcrest.admin as admin
    args = managesiteargs.parse_args()
    admin_url, rest_url = get_rest_urls(args.site)
    with action("connecting to admin site {0}".format(admin_url)):
        site = admin.Admin(admin_url, args.username, args.password,
                           generate_token=args.token)
        assert site._json_struct.get('status', 'ok') != 'error',\
               ' '.join(site._json_struct.get('messages',
                   ['Could not connect to site.']))
    with action("determining actions to perform"):
        assert any([
                     args.add_machines, 
                     args.remove_machines,
                     args.delete_cluster,
                     args.create_cluster,
                     args.list,
                     args.list_clusters,
                     args.operation
                ]), "No action specified (use --help for options)"
    operation = (args.operation or '').lower()
    if not args.list_clusters:
        with action("looking up cluster"):
            try:
                cluster = site.clusters[args.cluster] if args.cluster else None
            except KeyError:
                if args.create_cluster:
                    cluster = site.clusters.create(args.cluster)
                else:
                    raise
        with action("performing {0}".format(operation or '')):
            assert cluster, "No cluster specified"
            if operation.lower() == "start":
                cluster.start()
            elif operation.lower() == "stop":
                cluster.stop()
            elif operation == "chkstatus":
                raise NotImplementedError("Chkstatus not implemented")
        with action("deleting cluster"):
            if args.delete_cluster:
                assert cluster, "No cluster specified to delete"
                cluster.delete()
        with action("adding machines to cluster"):
            if args.add_machines:
                assert cluster, "No cluster specified"
                for machine in args.add_machines:
                    with action("adding {0} to cluster".format(machine)):
                        cluster.machines.add(machine)
        with action("removing machines from cluster"):
            if args.remove_machines:
                assert cluster, "No cluster specified"
                for machine in args.remove_machines:
                    with action("deleting {0} from cluster".format(machine)):
                        cluster.machines.remove(machine)
        with action("listing machines"):
            if args.list:
                name, itemobject = ('cluster', cluster) \
                        if cluster else ('site', site)
                print("===Machines on this {0}===".format(name))
                for machine in itemobject.machines.keys():
                    print("-", machine)
                print()
    elif args.list_clusters:
        with action("listing clusters"):
            if args.list_clusters:
                print("===Clusters on this site===")
                for cluster in site.clusters.clusterNames:
                    print("-", cluster)
                print()

deletecacheargs = argparse.ArgumentParser(description=
                                                'Deletes a map tile cache',
                                            parents=[shared_args])
deletecacheargs.add_argument('-n', '--name',
                               help='Description: Service name')
deletecacheargs.add_argument('-i', '--instances',
                             metavar="instances",
                             help="Number of instances",
                             default=1,
                             type=int)
deletecacheargs._optionals.title = "arguments"

@provide_narration
def deletecache(action):
    import arcrest.admin as admin
    args = deletecacheargs.parse_args()
    admin_url, rest_url = get_rest_urls(args.site)
    with action("connecting to REST services {0}".format(rest_url)):
        rest_site = Catalog(rest_url, args.username, args.password,
                            generate_token=args.token)
    with action("fetching reference to Delete Cache tool"):
        delete_cache_tool = (rest_site['System']
                                      ['CachingTools']
                                      ['DeleteCache'])
    with action("deleting map cache"):
        result_object = delete_cache_tool(args.name, args.instances)
        wait_on_tool_run(result_object)

managecachetilesargs = argparse.ArgumentParser(description=
                                                'Manage a map tile cache',
                                            parents=[shared_args])
managecachetilesargs.add_argument('-n', '--name',
                               help='Description: Service name')
managecachetilesargs.add_argument('-scales',
                                  metavar="scale",
                                  type=float,
                                  nargs='+',
                                  help=
                                   "Description: Scales to generate caches")
managecachetilesargs.add_argument('-mode', '--update-mode' ,
                                  help="Description: Update mode",
                                  choices=['Recreate_All_Tiles',
                                           'Recreate_Empty_Tiles',
                                           'Delete_Tiles'])
managecachetilesargs.add_argument('-i', '--instances',
                                  metavar="instances",
                                  help="Number of instances",
                                  type=int)
managecachetilesargs.add_argument('-f', '--feature-class',
                                  default=None,
                                  help="Description: Path to feature class")
managecachetilesargs.add_argument('-extent', '--cache-extent',
                                  metavar='"{xmin; ymin; xmax; ymax}"',
                                  help="Extent[s] to cache",
                                  nargs='+')
managecachetilesargs.add_argument('-wait', '--wait-for-completion',
                            help="Description: Wait for operation to complete",
                                  choices=['True', 'False'],
                                  default="True")
managecachetilesargs._optionals.title = "arguments"

@provide_narration
def managecachetiles(action):
    import arcrest.admin as admin
    args = managecachetilesargs.parse_args()
    admin_url, rest_url = get_rest_urls(args.site)
    with action("connecting to REST services {0}".format(rest_url)):
        rest_site = Catalog(rest_url, args.username, args.password,
                            generate_token=args.token)
    with action("fetching reference to Manage Cache tool"):
        manage_cache_tool = (rest_site['System']
                                      ['CachingTools']
                                      ['Manage Map Cache Tiles'])
    with action("managing map cache"):
        result_object = manage_cache_tool(args.site[:args.site.find('?')]
                                            if '?' in args.site
                                            else args.site,
                                          args.scales,
                                          args.instances,
                                          args.update_mode,
                                          args.cache_extent,
                                          args.area_of_interest)
    if args.wait_for_completion.lower() != "true":
        wait_on_tool_run(result_object)
    else:
        print (result_object.url)

createcacheschemaargs = argparse.ArgumentParser(description=
                                             'Creates a map tile cache schema',
                                            parents=[shared_args])
createcacheschemaargs.add_argument('-n', '--name',
                               help='Description: Service name')
createcacheschemaargs.add_argument('-Dc', '--cache_directory',
                               help='Description: ArcGIS Server Cache '
                                    'Directory')
createcacheschemaargs.add_argument('-scheme', '--tiling-scheme',
                               help='Description: Tiling scheme',
                               choices=['New', 'Predefined'])
createcacheschemaargs.add_argument('-X', '--tiling-scheme-path',
                               help='Description: Path to tiling scheme (if '
                                    'Predefined)',
                               default=None)
createcacheschemaargs.add_argument('-scales', '--scales-type',
                               help='Description: Scales',
                               choices=['Standard', 'Custom'])
createcacheschemaargs.add_argument('-number', '--number-of-scales',
                               help='Description: Number of scales (if Standard)',
                               default=1,
                               type=int,
                               metavar='1-20')
createcacheschemaargs.add_argument('-scale-values', '--custom-scale-values',
                               help='Description: Scales (if Custom)',
                               default="",
                               nargs='+',
                               metavar='scale')
createcacheschemaargs.add_argument('-dpi', '--DPI',
                               help='Description: DPI of tiles [0-100]',
                               type=int,
                               default=100,
                               metavar='0-100')
createcacheschemaargs.add_argument('-TS', '--tile-size',
                               help='Description: Tile size',
                               choices=['125x125', '256x256', '512x512', '1024x1024'],
                               default='125x125')
createcacheschemaargs.add_argument('-TO', '--tile-origin',
                               help='Description: Tile origin',
                               metavar='"(x, y)"')
createcacheschemaargs.add_argument('-TF', '--tile-format',
                               help='Description: Tile format',
                               choices=['PNG8', 'PNG24', 'PNG32', 'JPEG', 'MIXED'])
createcacheschemaargs.add_argument('-TC', '--tile-compression',
                               help='Description: Compression (if JPEG or MIXED)',
                               default=0,
                               type=int,
                               metavar='0-100')
createcacheschemaargs.add_argument('-storage', '--tile-storage-format',
                               help='Description: Tile storage format',
                               choices=['Compact', 'Exploded'])
createcacheschemaargs.add_argument('-use', '--use-local-cache-directory',
                               help='Description: Use local cache directory '
                                    '(if Compact)',
                               default='False',
                               choices=['True', 'False'])

createcacheschemaargs._optionals.title = "arguments"

@provide_narration
def createcacheschema(action):
    import arcrest.admin as admin
    args = createcacheschemaargs.parse_args()
    admin_url, rest_url = get_rest_urls(args.site)
    with action("connecting to REST services {0}".format(rest_url)):
        rest_site = Catalog(rest_url, args.username, args.password,
                            generate_token=args.token)
    with action("fetching reference to Import Cache tool"):
        create_cache_tool = (rest_site['System']
                                      ['CachingTools']
                                      ['Create Map Cache'])
    with action("creating map cache"):
        result_object = create_cache_tool(args.name,
                                          args.cache_directory,
                                          args.tile_origin,
                                          args.custom_scale_values
                                                if args.scales_type == 'Custom'
                                                else args.number_of_scales,
                                          args.tile_storage_format,
                                          args.tile_format,
                                          args.tile_compression,
                                          args.DPI,
                                          args.tile_size.split("x")[0],
                                          args.tile_size.split("x")[1],
                                          args.use_local_cache_directory == 'True')
        wait_on_tool_run(result_object)

convertcachestorageformatargs = argparse.ArgumentParser(
                                            description=
                                             'Convert the format of a stored '
                                             'map cache',
                                            parents=[shared_args])

convertcachestorageformatargs.add_argument('-n', '--name',
                                  metavar="service",
                                  help="Service name")
convertcachestorageformatargs.add_argument('-i', '--instances',
                                  metavar="instances",
                                  help="Number of instances",
                                  type=int)

convertcachestorageformatargs._optionals.title = "arguments"

@provide_narration
def convertcachestorageformat(action):
    import arcrest.admin as admin
    args = convertcachestorageformatargs.parse_args()
    admin_url, rest_url = get_rest_urls(args.site)
    with action("connecting to REST services {0}".format(rest_url)):
        rest_site = Catalog(rest_url, args.username, args.password,
                            generate_token=args.token)
    with action("fetching reference to Convert Cache Storage Format tool"):
        convert_cache_tool = (rest_site['System']
                                       ['CachingTools']
                                       ['Convert Cache Storage Format'])
    with action("converting format"):
        result_object = convert_cache_tool(args.name,
                                           args.instances)
        while result_object.running:
            time.sleep(0.125)
        print ("\n".join(msg.description for msg in result_object.messages))
