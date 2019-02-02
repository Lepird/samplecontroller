import json
import yaml
from kubernetes import client, config, watch
from kubernetes.client.models import V1ConfigMap, V1ObjectMeta
from kubernetes.client.rest import ApiException
import os

DOMAIN = "kool.karmalabs.local"
goodbrands = ['coleclark', 'fender', 'gibson', 'ibanez', 'martin', 'seagull', 'squier', 'washburn']
badbrands = ['epiphone', 'guild', 'gretsch', 'jackson', 'ovation', 'prs', 'rickenbauer', 'taylor', 'yamaha']

api_client = None


def update_counters(brand, operation):
    replace = True
    try:
        print ('getting conf')
        config_map = client.CoreV1Api(api_client).\
            read_namespaced_config_map(name='guitar-conf', namespace='fahad-test-guitar')  # type: V1ConfigMap
    except ApiException as e:
        if e.status == 404:
            replace = False
            print('new conf')
            config_map = V1ConfigMap(api_version='v1', data={brand: "0"}, kind='ConfigMap',
                                     metadata=V1ObjectMeta(name='guitar-conf'))
        else:
            print ('error in read of config map -- ' + e)
    except Exception as ex:
        print ('un handled exception in read config map -- ' + ex)

    try:
        print('getting counters')
        count = int(config_map.data[brand])
    except KeyError:
        print ('no counters')
        count = 0
    except Exception as ex:
        print ('exception in getting counters -- ' + ex)

    if operation == "DELETED":
        count -= 1
        if count < 0:
            count = 0
    else:
        count += 1
    config_map.data[brand] = str(count)
    print (brand + ' count= ' + str(count))

    ## test multi-line

    config_map.data["file.conf"] = "this is something\nand another\n    here is an indent"
    config_map.data["file2.conf"] = """
this is something
and another
    here is an indent
"""
    if replace:
        print('replacing conf')
        client.CoreV1Api(api_client).replace_namespaced_config_map(name='guitar-conf',
                                                                   namespace='fahad-test-guitar', body=config_map)
    else:
        print('creating conf')
        client.CoreV1Api(api_client).create_namespaced_config_map(namespace='fahad-test-guitar', body=config_map)


def review_guitar(crds, obj, operation):
    metadata = obj.get("metadata")
    if not metadata:
        print("No metadata in object, skipping: %s" % json.dumps(obj, indent=1))
        return
    name = metadata.get("name")
    brand = obj["spec"]["brand"]
    if operation != "DELETED":
        obj["spec"]["review"] = True
        namespace = metadata.get("namespace")
        if brand in goodbrands:
            obj["spec"]["comment"] = "this is a great instrument"
        elif brand in badbrands:
            obj["spec"]["comment"] = "this is shit"
        else:
            obj["spec"]["comment"] = "nobody knows this brand"

        print("Updating: %s" % name)
        #crds.replace_namespaced_custom_object(DOMAIN, "v1", namespace, "guitars", name, obj)
    update_counters(brand, operation)


if __name__ == "__main__":
    print(
        """
        asdasda
asdasdasd
adasdsad
asdsadsad"""
    )
    if 'KUBERNETES_PORT' in os.environ:
        config.load_incluster_config()
        definition = '/tmp/guitar.yml'
    else:
        config.load_kube_config()
        definition = 'guitar.yml'
    configuration = client.Configuration()
    configuration.assert_hostname = False
    api_client = client.api_client.ApiClient(configuration=configuration)
    v1 = client.ApiextensionsV1beta1Api(api_client)
    current_crds = [x['spec']['names']['kind'].lower() for x in v1.list_custom_resource_definition().to_dict()['items']]
    if 'guitar' not in current_crds:
        print("Creating guitar definition")
        with open(definition) as data:
            body = yaml.load(data)
        v1.create_custom_resource_definition(body)
    crds = client.CustomObjectsApi(api_client)

    print("Waiting for Guitars to come up...")
    resource_version = ''
    while True:
        stream = watch.Watch().stream(crds.list_cluster_custom_object, DOMAIN, "v1", "guitars",
                                      resource_version=resource_version)
        for event in stream:
            obj = event["object"]
            operation = event['type']
            spec = obj.get("spec")
            if not spec:
                continue
            metadata = obj.get("metadata")
            resource_version = metadata['resourceVersion']
            name = metadata['name']
            print("Handling %s on %s" % (operation, name))
            done = spec.get("review", False)
            if done and operation != "DELETED":
                continue
            review_guitar(crds, obj, operation)
