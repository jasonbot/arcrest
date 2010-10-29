from __future__ import print_function

import argparse
import sys

import arcrest.admin

__all__ = ['createservice', 'manageservice', 'managesite']

shared_args = argparse.ArgumentParser(add_help=False)
shared_args.add_argument('-u', '--username', 
                         nargs=1,
                         default=None,
                         help='Username for Server')
shared_args.add_argument('-p', '--password', 
                         nargs=1,
                         default=None,
                         help='Password for Server')
shared_args.add_argument('-s', '--site', 
                         nargs=1,
                         default='http://127.0.0.1:6080/arcgis/admin/',
                         help='URL for admin Server')

createserviceargs = argparse.ArgumentParser(description='Creates a service',
                                            parents=[shared_args])
createserviceargs.add_argument('-c', '--cluster',
                               nargs=1,
                               default=None,
                               help='Name of cluster')

manageserviceargs = argparse.ArgumentParser(description=
                                                'Manages/modifies a service',
                                            parents=[shared_args])
manageserviceargs.add_argument('-n', '--name',
                               nargs=1,
                               default=None,
                               help='Service name')
manageserviceargs.add_argument('-o', '--operation',
                               nargs=1,
                               default=None,
                               help="status|start|stop|delete")

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
                               nargs=1,
                               help='chkstatus|start|stop')
managesiteargs.add_argument('-c', '--cluster',
                               nargs=1,
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


class ActionNarrator(object):
    def __init__(self):
        self.action_stack = []
    def __call__(self, action):
        self.action = action
        return self
    def __enter__(self):
        self.action_stack.append(self.action)
        pass
    def __exit__(self, t, ex, tb):
        action = self.action_stack.pop()
        if (t, ex, tb) != (None, None, None):
            if t is not SystemExit:
                print("Error %s: %s" % (action, str(ex)))
            sys.exit(1)

def provide_narration(fn):
    def fn_():
        return fn(ActionNarrator())
    return fn_

@provide_narration
def createservice(action):
    args = createserviceargs.parse_args()
    print(args)
    raise NotImplementedError("Not Implemented")

@provide_narration
def manageservice(action):
    args = manageserviceargs.parse_args()
    print(args)
    raise NotImplementedError("Not Implemented")

@provide_narration
def managesite(action):
    args = managesiteargs.parse_args()
    site = arcrest.admin.Admin(args.site)
    with action("determining actions to perform"):
        assert any([
                     args.add_machines, 
                     args.remove_machines,
                     args.delete_cluster,
                     args.create_cluster,
                     args.list,
                     args.list_clusters
                ]), "No action specified (use --help for options)"
    with action("looking up cluster"):
        try:
            cluster = site.clusters[args.cluster[0]] if args.cluster else None
        except KeyError:
            if args.create_cluster:
                cluster = site.clusters.create(args.cluster[0])
            else:
                raise
    with action("deleting cluster"):
        if args.delete_cluster:
            assert cluster, "Asked to delete a cluster when none was specified"
            cluster.delete()
    with action("adding machines to cluster"):
        if args.add_machines:
            assert cluster, "No cluster specified"
            for machine in args.add_machines:
                with action("adding %s to cluster" % machine):
                    cluster.machines.add(machine)
    with action("removing machines from cluster"):
        if args.remove_machines:
            assert cluster, "No cluster specified"
            for machine in args.remove_machines:
                with action("deleting %s from cluster" % machine):
                    cluster.machines.remove(machine)
    with action("listing machines"):
        if args.list:
            name, itemobject = ('cluster', cluster) if cluster else ('site', site)
            print("===Machines on this %s===" % name, end='')
            for machine in itemobject.machines.keys():
                print("*", machine)
            print()
    with action("listing clusters"):
        if args.list_clusters:
            print("===Clusters on this site===")
            for cluster in site.clusters.clusterNames:
                print("*", cluster)
            print()
