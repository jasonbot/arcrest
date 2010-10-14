import argparse

__all__ = ['createservice', 'manageservice']

shared_args = argparse.ArgumentParser(add_help=False)
shared_args.add_arguments('-u')

createserviceargs = argparse.ArgumentParser(description='Creates a service',
                                            parents=[shared_args])

manageserviceargs = argparse.ArgumentParser(description=
                                                'Manages/modifies a service',
                                            parents=[shared_args])

def createservice():
    args = createserviceargs.parse_args()    

def manageservice():
    args = manageserviceargs.parse_args()
