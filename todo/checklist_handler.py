from todo.connection import TrelloConnection
import yaml
import trello
import time
import re
from tqdm import tqdm


class Checklist(object):
    def __init__(self, id, connection, name, items, checks):
        self.id = id
        self.connection = connection
        self.name = name
        self.items = items
        self.checks = checks

    def add_to_trello(self):
        json_obj = self.connection.trello.fetch_json(
            '/cards/' + self.id + '/checklists',
            http_method='POST',
            post_args={'name': self.name}, )
        cl = trello.checklist.Checklist(self.connection.trello, [], json_obj, trello_card=self.id)
        for text, checked in zip(self.items, self.checks):
            cl.add_checklist_item(text, checked=checked)
        return cl


class ChecklistHandler:
    def __init__(self, connection: TrelloConnection, id, checklists):
        self.connection = connection
        self.id = id
        self.checklists = checklists
        self.new_checklist = None

    def parse_checklists(self):
        checklists_to_edit = ""
        for checklist in self.checklists:
            items = []
            for item in checklist.items:
                if item['state'] == 'complete':
                    items.append("[x] " + item['name'])
                elif item['state'] == 'incomplete':
                    items.append("[ ] " + item['name'])
            yaml_checklist = {checklist.name.replace("\n", ""): items}
            checklists_to_edit += yaml.dump(yaml_checklist, default_flow_style=False) + "\n"
        return checklists_to_edit


    def parse_item_string(self, line):
        line = line.lstrip()
        line = line[1:].split("] ")
        if line[0] == "x" or line[0] == "X":
            return line[1], True
        elif line[0] == " ":
            return line[1], False

    def create_objects_from_list(self, l_checklists):
        checklist_objects = []
        for checklist in l_checklists:
            name = list(checklist.keys())[0]
            checklist_items = list(checklist.values())[0]
            checks = []
            texts = []
            for item in checklist_items:
                text, checked = self.parse_item_string(item)
                checks.append(checked)
                texts.append(text)
            this_checklist = Checklist(id=self.id, connection=self.connection, name=name, items=texts, checks=checks)
            checklist_objects.append(this_checklist)
        return checklist_objects

    def parse_edited_checklists(self, new_checklists_edited):
        try:
            cleaned_checklist_string = self.clean_checklist_string(new_checklists_edited)
            l_checklists = [yaml.safe_load(item) for item in cleaned_checklist_string.split("\n\n")]
            checklist_objects = self.create_objects_from_list(l_checklists=l_checklists)
            print("Parsing successful!")
        except AttributeError:
            print("Cannot parse the checklists from editor! YAML file not valid!")
            print("Opening editor again")
            time.sleep(3)
            return None, False
        except yaml.scanner.ScannerError:
            print("ScannerError! YAML file not valid!")
            print("Opening editor again")
            time.sleep(3)
            return None, False
        except:
            print("Unknown error!")
            print("Opening editor again")
            time.sleep(3)
            return None, False

        new_checklists = []
        print("Adjusting checklists...")
        for checklist in tqdm(checklist_objects):
            cl = checklist.add_to_trello()
            new_checklists.append(cl)
        return new_checklists, True

    def clean_checklist_string(self, checklist_string):
        cleaned_checklist_string = checklist_string

        while cleaned_checklist_string.endswith("\n"):
            cleaned_checklist_string = cleaned_checklist_string[:-1]

        while cleaned_checklist_string.startswith("\n"):
            cleaned_checklist_string = cleaned_checklist_string[1:]

        while cleaned_checklist_string != cleaned_checklist_string.replace("\n\n\n", "\n\n"):
            cleaned_checklist_string = cleaned_checklist_string.replace("\n\n\n", "\n\n")

        while cleaned_checklist_string != cleaned_checklist_string.replace("]\n\n", "]\n"):
            cleaned_checklist_string = cleaned_checklist_string.replace("]\n\n", "]\n")

        while cleaned_checklist_string != cleaned_checklist_string.replace("\t", "  "):
            cleaned_checklist_string = cleaned_checklist_string.replace("\t", "  ")

        while cleaned_checklist_string != cleaned_checklist_string.replace("[]", "[ ]"):
            cleaned_checklist_string = cleaned_checklist_string.replace("[]", "[ ]")

        cleaned_checklist_string = re.sub(r"\n\n(\s+)\[", r"\n      [", cleaned_checklist_string)
        cleaned_checklist_string = re.sub(r"](\s+)(\w)", r"] \2", cleaned_checklist_string)
        cleaned_checklist_string = re.sub(r"\[(\w)\](\w)", r"[\1]] \2", cleaned_checklist_string)
        cleaned_checklist_string = re.sub(r"\n\n-", r"\n-", cleaned_checklist_string)

        return cleaned_checklist_string

    def remove_old_checklists(self):
        print("Cleaning checklists...")
        for old_checklist in tqdm(self.checklists):
            old_checklist.delete()
