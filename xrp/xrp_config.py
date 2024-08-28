import json

#
# Function to read a JSON formatted config file with the XRP configuration
# information. Calling function can optionally specify a top-level configuration
# section if the program only needs a piece of the configuration.
#
def read_config( filename='config.json', section=None ):
    data = ''

    with open( filename ) as fd:
        try:
            data = json.load(fd)
            if section:
                data = data.get(section, None)
        except ValueError as err:
            print( err )
    return data
