from gtd import parse_configuration, GTD_Controller, GTD_Display
import trello
import pytest

def test_parse_configuration():
    # open and parse our example configs
    properties = parse_configuration('gtd.yaml.example')
    assert properties == {
        'board_name': 'GTD',
        'list_names': {
            'blocked': 'Blocked',
            'done': 'Done',
            'holding': 'Holding',
            'in_progress': 'Doing',
            'incoming': 'Incoming',
            'projects': 'Projects',
            'reference': 'Reference',
            'someday': 'Ideas'
        },
        'testing_board_name': 'Unused',
        'trello': {
            'api_key': 'your-api-key',
            'api_secret': 'your-api-secret',
            'oauth_token': 'your-oauth-token',
            'oauth_token_secret': 'your-oauth-secret'
        }
    }

class TestGTDControllerInitialization:
    def test_initialize_trello(self):
        '''initialize the trello client as we normally would
        '''
        configs = parse_configuration()
        g = GTD_Controller(configs, None)
        # make sure the trello client and target board were bound
        assert type(g.trello) == trello.TrelloClient
        assert type(g.board) == trello.Board
        # make sure all the list IDs are set up correctly
        assert type(g.lists) == dict
        assert all(isinstance(e, str) for _, e in g.lists.items())

    def test_bad_trello_key(self):
        '''test the case where we pass invalid trello creds
        '''
        configs = parse_configuration('gtd.yaml.example')
        with pytest.raises(trello.Unauthorized):
            g = GTD_Controller(configs, None)
