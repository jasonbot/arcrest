import argparse

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
                         default=None, #'http://127.0.0.1:6080/arcgis/admin/',
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
                               help='Machines to add to site')
managesiteargs.add_argument('-R', '--remove-machines',
                               nargs='+',
                               help='Machines to remove from site')
managesiteargs.add_argument('-l', '--list',
                               default=False,
                               action='store_true',
                               help='List of machines on a site')
managesiteargs.add_argument('-o', '--operation',
                               nargs=1,
                               help='chkstatus|start|stop')
managesiteargs.add_argument('-D', '--delete-cluster',
                               default=False,
                               action='store_true',
                               help='Delete this cluster')


def createservice():
    args = createserviceargs.parse_args()
    print args
    raise NotImplementedError("Not Implemented")

def manageservice():
    args = manageserviceargs.parse_args()
    print args
    raise NotImplementedError("Not Implemented")

def managesite():
    args = managesiteargs.parse_args()
    print args
    raise NotImplementedError("Not Implemented")
