import argparse

__all__ = ['createservice', 'manageservice']

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

manageserviceargs = argparse.ArgumentParser(description=
                                                'Manages/modifies a service',
                                            parents=[shared_args])

def createservice():
    args = createserviceargs.parse_args()    

def manageservice():
    args = manageserviceargs.parse_args()
