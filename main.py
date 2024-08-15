import boto3
import os
from diagrams import Cluster, Diagram
from diagrams.aws.management import OrganizationsAccount
from diagrams.aws.management import OrganizationsAccount,OrganizationsOrganizationalUnit,Organizations





def handler():
    os.environ["AWS_DEFAULT_REGION"] = 'us-east-1'
    org = boto3.client('organizations')
    org_ous = {}
    scpsInOu = {}
    # get org ous and scps
    def walkOrg(parent=None,chain=['root']):
        if not parent:
            for root in org.list_roots()["Roots"]:
                walkOrg(parent=root["Id"],chain=[*chain])
        else:
            ouChildren = org.list_children(ParentId=parent,ChildType='ORGANIZATIONAL_UNIT')["Children"]
            for ouChild in ouChildren:
                name = org.describe_organizational_unit(OrganizationalUnitId=ouChild["Id"])["OrganizationalUnit"]["Name"]
                org_ous[name] = chain
                if name not in scpsInOu:
                    scpsInOu[name] = [p["Name"] for p in org.list_policies_for_target(TargetId=ouChild["Id"],Filter='SERVICE_CONTROL_POLICY')["Policies"]]
                walkOrg(parent=ouChild["Id"],chain=[*chain,name])
    
    walkOrg()
    # make a tree of the org ous
    TREE = {}
    def make_tree(data,*args):
        if not len(args):
            return data
        value = args[0]
        if not data.get(value):
            data[value] = {}
        make_tree(data[value],*args[1:])
    for k,v in org_ous.items():
        make_tree(TREE,*v, k)
    # walk the ou tree and create diagram
    with Diagram("AWS Organization", show=False, direction="TB"):
        def walk_tree(tree,root):
            for k,v in tree.items():
                scps = f"{k} permissions\n"
                if len(scpsInOu[k]):
                    scps += '\n'.join(scpsInOu[k])
                else: 
                    scps += 'none'
                with Cluster(scps):
                    punit = OrganizationsOrganizationalUnit(k)
                    root >> punit
                    for y,z in v.items():
                        scps = f"{y} permissions\n"
                        if len(scpsInOu[y]):
                            scps += '\n'.join(scpsInOu[y])
                        else: 
                            scps += 'none'
                        with Cluster(scps):
                            unit = OrganizationsOrganizationalUnit(y)
                            punit >> unit
                            if len(z):
                                walk_tree(z, unit)

        with Cluster('organization'): 
            root = OrganizationsAccount('root')         
            walk_tree(TREE["root"],root)


handler()
