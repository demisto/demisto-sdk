import requests


# The function receives a json object
# and returns a string-type variable
# that contains the required values in Markdown syntax
def build_tables(result):
    out_put = '**Rocket general details**\n' \
              '| Rocket Name | First flight | Is Active |\n' \
              '|--|--|--|\n' \
              '| ' + str(result['rocket_id']) + ' | ' + result['first_flight'] + ' | ' + str(result['active']) + ' |\n'

    out_put += '**Technical details**\n' \
               '| Height | Mass |\n' \
               '|--|--|\n' \
               '| ' + str(result['height']['meters']) + ' | ' + str(result['mass']['kg']) + ' |\n'

    out_put += '**Images Links**\n' \
               '|[' + result['flickr_images'][0] + '](' + result['flickr_images'][0] + ')|\n' \
               '|--| \n'

    for i in range(1, len(result['flickr_images'])):
        out_put += '|**[' + result['flickr_images'][i] + '](' + result['flickr_images'][i] + ')**|\n'

    return out_put


def rocket_details(rocketID):

    # Check the rocketID type & length
    if type(rocketID) != str or len(rocketID) == 0:
        return "The rocketID must be of type string, And must contain at least one character"

    base_url = "https://api.spacexdata.com/v3/rockets/"

    response = requests.request("GET", base_url + rocketID)

    # When the rocket ID does not exist
    if response.status_code == 404:
        return "Page not found (Incorrect rocket ID)"

    # If all is well, (but still have a problem if we send in the rocketID characters like "?" Or "#")
    if response.status_code == 200:
        try:
            data = response.json()
            return build_tables(data)
        except Exception as e:
            return e

    # All other situations
    return "There is a problem, status code " + str(response.status_code)
