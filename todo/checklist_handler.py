from todo.connection import TrelloConnection
import trello
import re


class ChecklistHandler:
    def __init__(self, connection: TrelloConnection, id, checklists):
        self.connection = connection
        self.id = id
        self.checklists = checklists
        self.new_checklist = None

    def parse_checklists(self):
        checklists_to_edit = ""
        for checklist in self.checklists:
            checklists_to_edit += "{name}:\n".format(
                                  name=checklist.name.replace("\n", " "))
            for item in checklist.items:
                if item['state'] == 'complete':
                    checklists_to_edit += ' ' * 6 + "[x] " + item['name'] + "\n"
                elif item['state'] == 'incomplete':
                    checklists_to_edit += ' ' * 6 + "[ ] " + item['name'] + "\n"
            checklists_to_edit += "\n"
        return checklists_to_edit

    def parse_edited_checklists(self, new_checklists_edited):
        cleaned_checklist_string = self.clean_checklist_string(new_checklists_edited)

        new_checklists = []
        for checklist in cleaned_checklist_string.split("\n\n"):
            splitted_lines = checklist.split(":\n")
            name = splitted_lines[0].split(":")[0]

            json_obj = self.connection.trello.fetch_json(
                '/cards/' + self.id + '/checklists',
                http_method='POST',
                post_args={'name': name}, )

            cl = trello.checklist.Checklist(self.connection.trello, [], json_obj, trello_card=self.id)

            for line in splitted_lines[1].splitlines():
                line = line.lstrip()
                line = line[1:].split("] ")
                if line[0] == "x" or line[0] == "X":
                    cl.add_checklist_item(line[1], checked=True)
                elif line[0] == " ":
                    cl.add_checklist_item(line[1], checked=False)
            new_checklists.append(cl)
        return new_checklists


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

        cleaned_checklist_string = re.sub(r"\n\n(\s+)\[", "\n      [", cleaned_checklist_string)
        cleaned_checklist_string = re.sub(r"](\s+)(\w)", r"] \2", cleaned_checklist_string)
        cleaned_checklist_string = re.sub(r"\[(\w)\](\w)", r"[\1]] \2", cleaned_checklist_string)

        return cleaned_checklist_string


    def remove_old_checklists(self):
        for old_checklist in self.checklists:
            old_checklist.delete()
