import appdirs

def get_golem_datadir(mainnet=False):
    """ Helper function for golem datadir
    """
    if mainnet:
        DATA_DIR = 'mainnet'
    else:
        DATA_DIR = 'rinkeby'

    return os.path.join(
        os.path.join(appdirs.user_data_dir('golem'), 'default'),
        DATA_DIR
    )
