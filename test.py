import demisto_client.demisto_api
from demisto_client.demisto_api.rest import ApiException
from pprint import pprint

api_key = '4321C4089DD6F52370E5BD00CE19A95B'
base_url = 'http://localhost:8080'

# api_instance = demisto_client.configure(base_url=base_url, api_key=api_key, verify_ssl=False)
# filter_ = demisto_client.demisto_api.SearchIncidentsData()
# inc_filter = demisto_client.demisto_api.IncidentFilter()
# inc_filter.query = 'name:test'
# filter_.filter = inc_filter
#
# update_data_batch = demisto_client.demisto_api.UpdateDataBatch()
# update_data_batch.filter = inc_filter
#
# incidents_csv = api_instance.export_incidents_to_csv_batch(update_data_batch=update_data_batch)
# pprint(api_instance.download_file(entryid=incidents_csv))


import demisto_client.demisto_api
from demisto_client.demisto_api.rest import ApiException
from pprint import pprint

api_instance = demisto_client.configure(base_url=base_url, api_key=api_key)
id = 80 # str | CSV file to fetch (returned from batch export to csv call)

try:
    # Get incident as CSV
    api_response = api_instance.get_incident_as_csv(id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DefaultApi->get_incident_as_csv: %s\n" % e)