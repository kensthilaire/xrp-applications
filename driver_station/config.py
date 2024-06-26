
import json
from logger import logger
import sys

CONFIG_FILENAME = None

def update_config_params(param_label, config_data):
    curr_config = read_config()
    curr_config[param_label] = config_data
    save_config( curr_config ) 
    logger.info( 'Configuration Parameters For %s Updated' % param_label )

def update_full_config( config_data ):
    curr_config = read_config()
        
    logger.info( 'New Config: %s' % json.dumps(config_data) )
    for section, section_cfg in config_data.items():
        config_section = curr_config.get( section ) 
        if config_section == None:
            logger.info( 'Adding New Config: %s' % json.dumps(section) )
            curr_config[section] = section_cfg
        else:
            logger.info( 'Existing Config: %s' % json.dumps(config_section) )
            for param, param_cfg in section_cfg.items():
                config_section[param] = param_cfg

    save_config( curr_config )

def add_syntax_correction_suggestion( msg ):
    if msg.startswith('Expecting property name enclosed in double quotes'):
        logger.error( 'Check for extra trailing comma in line above this one')
    elif msg.startswith('Expecting \',\' delimiter'):
        logger.error( 'Check for missing trailing comma in line above this one')
    elif msg.startswith('Expecting value'):
        logger.error( 'Did you use single quotes when specifying a string parameter, need double-quotes')

def read_config( filename='config.json' ):
    global CONFIG_FILENAME
    CONFIG_FILENAME = filename

    data = ''
    with open( filename ) as fd:
        try:
            data = json.load(fd)
        except ValueError as err:
            logger.error( 'Error parsing JSON configuration file: %s' % filename )
            logger.error( err )
            add_syntax_correction_suggestion( str(err) )
            sys.exit(1)

    return data

def save_config( config_dict, filename='config.json' ):

    with open( filename, 'w' ) as fd:
        fd.write( json.dumps(config_dict, indent=4) )

