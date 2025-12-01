import requests
import os
import re
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config/config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r', encoding='utf-8') as CONFIG:
        CONFIG_FILE = json.load(CONFIG)
    print("Configuration file loaded successfully.")
else:
    CONFIG_FILE = {}
    print("Configuration file not found. Using default configuration.")

UNTIS_URL = CONFIG_FILE.get("UNTIS_URL", "")

def _reload_texts():
    global texts
    with open('./texte.json', 'r', encoding='utf-8') as file:
        texts = json.load(file)

def _get_date(day, String):
    regex = "(.*?)" + day
    match = re.search(regex, String)
    if match:
        return_value = match.group(1)

    return_value = re.sub(r"\s*", "", return_value)

    return return_value

def _text_formatting(text_string, clas):
    text_string = re.sub("<.*?>", " ", text_string)

    if re.search(".*?Montag", text_string):
        searched_day = "Montag" 
        searched_date = _get_date(searched_day, text_string)
    elif re.search(".*?Dienstag", text_string):
        searched_day = "Dienstag" 
        searched_date = _get_date(searched_day, text_string)
    elif re.search(".*?Mittwoch", text_string):
        searched_day = "Mittwoch" 
        searched_date = _get_date(searched_day, text_string)
    elif re.search(".*?Donnerstag", text_string):
        searched_day = "Donnerstag" 
        searched_date = _get_date(searched_day, text_string)
    elif re.search(".*?Freitag", text_string):
        searched_day = "Freitag" 
        searched_date = _get_date(searched_day, text_string)

    text_string = re.sub(".*?Montag | .*?Dienstag | .*?Mittwoch | .*?Donnerstag | .*?Freitag", " ", text_string)

    lines = text_string.split('\n')
    new_string = ''

    filter1 = re.split(r'(\d+)', clas)[1]
    filter2 = re.split(r'(\d+)', clas)[2]
    filter = filter1 + "[A-Za-z]*?" + filter2

    for line in lines:
        if re.search(filter, line):
            new_string += line + '\n'
    text_string = new_string

    lines = text_string.split('\n')
    lines = [line for line in lines if line.strip()]
    text_string = '\n'.join(lines)

    text_string = re.sub("&nbsp;", "---", text_string)

    return text_string, searched_day, searched_date

def _process_line(line):
    if re.match(r'^[|\s]+$', line):
        return None
    else:
        return line
    
def _add_pipe(text):
    lines = text.split('\n')
    updated_lines = [
        line + ' | ' if any(c.isalpha() for c in line) and not line.strip().endswith('|') else line
        for line in lines
    ]
    result = '\n'.join(updated_lines)
    return result

def _add_pipe_prefix(text):
    lines = text.split('\n')
    updated_lines = [' |' + line if re.search('[A-Za-z]', line) and not line.startswith(' | ') else line for line in lines]
    updated_text = '\n'.join(updated_lines)
    return updated_text

def _day(day, clas):
    if clas == "header":
        header = True
        clas = "11n"
    else:
        header = False
    source_url = UNTIS_URL+str(day)+'.htm'
    response = requests.get(source_url)
    source_html = response.text
    if response.text.find("Keine Vertretungen</td>") != -1 or response.text.find("Keine Vertretungen </td>") != -1:
        funktion_return = _text_formatting(response.text, clas)
        searched_day = funktion_return[1]
        searched_date = funktion_return[2]
        return "Der Vertretungsplan wurde für " +  searched_day + ", den " + searched_date + " noch nicht aktuallierst/erstellt."
    source_html = re.sub(r'style="background-color: #FFFFFF"', '', source_html)
    source_html = re.sub(r'<html>', '', source_html, flags=re.DOTALL)
    source_html = re.sub(r'<head>', '', source_html, flags=re.DOTALL)
    source_html = source_html.replace('<table class="mon_head">', '', 1)
    if header:
        funktion_return = _text_formatting(response.text, clas)
        searched_day = funktion_return[1]
        searched_date = funktion_return[2]
    if header:
        pattern = re.compile(r'<table class="info"[^>]*>(.*?)</table>', re.DOTALL)
        matches1 = pattern.findall(source_html)
        if matches1:
            for match in matches1:
                matches1_content = match
                matches1_content = matches1_content.replace('<tr class="info">', '<tr class="info_content">')
                matches1_content = matches1_content.replace("<tr class='info'>", '<tr class="info_content">')

                Raeume = re.compile(r'R.ume', re.DOTALL)
                Schulcafe = re.compile(r'Schulcaf.', re.DOTALL)
                Cafe = re.compile(r'Caf.', re.DOTALL)
                wuenschen = re.compile(r'w.nschen', re.DOTALL)
                schoene = re.compile(r'sch.ne', re.DOTALL)
                moeler = re.compile(r'M.lr', re.DOTALL)
                Fur = re.compile(r'F.r', re.DOTALL)
                fur = re.compile(r'f.r', re.DOTALL)
                Schueler = re.compile(r'Sch.ler', re.DOTALL)
                schueler = re.compile(r'sch.ler', re.DOTALL)
                Soe = re.compile(r'S[^a-zA-Z]', re.DOTALL)
                Due = re.compile(r'D[^a-zA-Z]', re.DOTALL)
                eigenstaendig = re.compile(r'eigenst.ndig', re.DOTALL)
                Krueger = re.compile(r'Kr.ger', re.DOTALL)
                Praeventionsveranst = re.compile(r'Pr.ventionsveranst', re.DOTALL)

                matches1_content = re.sub(Raeume, "Räume", matches1_content)
                matches1_content = re.sub(Schulcafe, "Schulcafé; ", matches1_content)
                matches1_content = re.sub(Cafe, "Café; ", matches1_content)
                matches1_content = re.sub(wuenschen, "wünschen", matches1_content)
                matches1_content = re.sub(schoene, "schöne", matches1_content)
                matches1_content = re.sub(moeler, "Mölr", matches1_content)
                matches1_content = re.sub(Fur, "Für", matches1_content)
                matches1_content = re.sub(fur, "für", matches1_content)
                matches1_content = re.sub(Schueler, "Schüler", matches1_content)
                matches1_content = re.sub(schueler, "schüler", matches1_content)
                matches1_content = re.sub(Soe, "Sö", matches1_content)
                matches1_content = re.sub(Due, "Dü", matches1_content)
                matches1_content = re.sub(eigenstaendig, "eigenständig", matches1_content)
                matches1_content = re.sub(Krueger, "Krüger", matches1_content)
                matches1_content = re.sub(Praeventionsveranst, "Präventionsveranst", matches1_content)

                matches1_content = re.sub("<.*?>", "", matches1_content)
                matches1_content = re.sub(" {2,}", " | ", matches1_content)
                matches1_content = re.sub("Lehrer&nbsp;", "Lehrer", matches1_content)
                matches1_content = re.sub("Klassen&nbsp;", "Klassen", matches1_content)
                matches1_content = re.sub("Räume&nbsp;", "Räume", matches1_content)
                matches1_content = re.sub("  Klassen", "Klassen", matches1_content)
                matches1_content = re.sub("LRSöbei", "LRS bei", matches1_content)

                lines = matches1_content.splitlines()

                output = """"""
                for line in lines:
                    processed_line = _process_line(line)
                    if processed_line is not None:
                        output += processed_line + "\n"

                matches1_content = output

                matches1_content = _add_pipe(matches1_content)

                matches1_content = _add_pipe_prefix(matches1_content)
        else:
            _reload_texts()
            return_value = texts.get('Error_Message_1','')
            return return_value

    else:
        pattern = re.compile(r'<table class="mon_list"[^>]*>(.*?)</table>', re.DOTALL)
        matches2 = pattern.findall(source_html)
        if matches2:
            for match in matches2:
                matches2_content = match
                Cafe1 = re.compile(r'Caf[^a-zA-Z] 1', re.DOTALL)
                Cafe2 = re.compile(r'Caf[^a-zA-Z] 2', re.DOTALL)

                matches2_content = re.sub(Cafe1, "Caf&#233; 1", matches2_content)
                matches2_content = re.sub(Cafe2, "Caf&#233; 2", matches2_content)

                funktion_return = _text_formatting(matches2_content, clas)
                matches2_content = funktion_return[0]
                searched_day = funktion_return[1]
                searched_date = funktion_return[2]

        else:
            _reload_texts()
            return_value = texts.get('Error_Message_2','')
            return return_value
    

    if header:
        return_value = matches1_content
    else:
        return_value = matches2_content


    if return_value == '':
        return_value = 'Keine Vertretungen für '+ searched_day + ', den ' + searched_date + ' gefunden.'
    else:
        if not header:
            return_value = re.sub(" {2,}", " | ", return_value)
            lines = return_value.split('\n')
            lines = [line.lstrip() for line in lines]
            return_value = '\n\n'.join(lines)
            return_value = "Vertretungen für "+ searched_day +", den " + searched_date + ":\n" + return_value
        else:
            matches1_content = re.sub(r'^[| ]+$\n?', '', matches1_content, flags=re.MULTILINE)
            return_value = "Wetere Informationen zu "+ searched_day +", den " + searched_date + ":" + return_value + "\n"
            
    return return_value