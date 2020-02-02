#!/usr/bin/env python3

import requests
import re
from lxml import html

ROOT_URL = 'https://gamefaqs.gamespot.com/switch/' \
    '230454-hyrule-warriors-definitive-edition/faqs/73095/'
MAP_NAMES = [
    "Adventure Map",
    "Great Sea Map",
    "Master Quest Map",
    "Master Wind Waker Map",
    "Twilight Map",
    "Termina Map",
    "Koholint Island Map",
    "Grand Travels Map",
    "Lorule Map",
]
MAP_NAME_TO_PATH = {
    "Adventure Map": 'adventure-map',
    "Great Sea Map": 'great-sea-map',
    "Master Quest Map": 'master-quest-map',
    "Master Wind Waker Map": 'master-wind-waker-map',
    "Twilight Map": 'twilight-map',
    "Termina Map": 'termina-map',
    "Koholint Island Map": 'koholint-island-map',
    "Grand Travels Map": 'grand-travels-map',
    "Lorule Map": 'lorule-map',
}
INT_HTML_FILE_NAME = 'index.html'
HEADERS = {'user-agent': 'my-grab/0.0.1'}
DIFFICULTY_MAP = {
    '000000': 0,
    '008000': 1,
    'ff9900': 2,
    '800080': 3,
    'ff6600': 4,
    '0000ff': 5,
    'ff0000': 6,
}
VALID_MISSION_HEADERS = [
    "Mission", "Search", "A-Rank Victory", "Battle Victory", "Treasure",
    "A-Rank KOs", "A-Rank Damage", "Notes",
    # "A-Rank Time",
]
ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


class Driver:
    def run(self):
        page_htmls = {}
        for name, path in MAP_NAME_TO_PATH.items():
            print("Gathering HTML for {}".format(name))
            page_htmls[name] = self._gather_map_page(path)

        page_dicts = {}
        for name, page_html in page_htmls.items():
            print("Converting HTML to dict for {}".format(name))
            page_dicts[name] = self._parse_page_html_to_dict(name, page_html)

        self._write_interactive_html(page_dicts)

    def _gather_map_page(self, map_path):
        return requests.get(ROOT_URL + map_path, headers=HEADERS).content

    def _parse_page_html_to_dict(self, name, page_html):
        page_tree = html.fromstring(page_html)
        # Need to find map by searching for a cell's exact text.
        # Searching for A-2 because Twilight does not have A-1.
        # Also grabbing checking for text-color style, because the Great
        # Sea page has an earlier tag with A-2 text that is not the map.
        page_dict = self._parse_map_table_node_to_dict(page_tree.xpath(
            '//*[text()="A-2"][contains(@style,"color")]/ancestor::tbody')[-1])
        for cell_loc, cell_dict in page_dict.items():
            if cell_loc == "size":
                continue
            # Find the header (e.g. Adventure Map A-1) and then the following
            # node, which should be the mission table.
            xpath = (
                '//h4[text()="{} {}"]/following-sibling::table[1]/tbody'
            ).format(name, cell_loc)
            # SBAllen apparently doesn't clean their HTML at all.
            # The header for Grand Travels Map P-2 has an anomalous
            # <strong> tag around the 2. And only the 2. Wut.
            if name == "Grand Travels Map" and cell_loc == "P-2":
                xpath = (
                    '//h4[text()="Grand Travels Map P-"]'
                    '/following-sibling::table[1]/tbody')
            elif name == "Lorule Map" and cell_loc == "A-3":
                xpath = (
                    '//h4[text()="tulLorule Map A-3"]'
                    '/following-sibling::table[1]/tbody')

            cell_dict['mission-data'] = self._parse_mission_node_to_dict(
                page_tree.xpath(xpath)[0])

        return page_dict

    def _parse_map_table_node_to_dict(self, map_table_node):
        map_dict = {
            "size": [len(map_table_node), len(map_table_node[0])]
        }
        for td in map_table_node.xpath('.//td'):
            if td.text_content() == " ":
                continue
            cell_loc = td.text_content()

            # Now find a child node which contains the background-color style.
            style_node = td.xpath(
                './/*[contains(@style,"background-color")]')
            color_match = re.search(
                r'background-color:\s*#([0-9A-Fa-f]*)',
                style_node[0].attrib['style'] if len(style_node) > 0 else "")
            color = color_match.group(1) if color_match else "invalid"
            if color in DIFFICULTY_MAP:
                color = DIFFICULTY_MAP[color]
            else:
                print("  Invalid color \"{}\" for cell_loc {}".format(
                    color, cell_loc))

            map_dict[cell_loc] = {"difficulty": color}

        return map_dict

    def _parse_mission_node_to_dict(self, mission_node):
        mission_dict = {}
        rows = mission_node.xpath('./tr')
        for i in range(0, len(rows), 2):
            if i == len(rows) - 1:
                print("  Mission table with odd number of rows")
                continue
            if len(rows[i]) != len(rows[i+1]):
                print("  Mission table with mismatched headers and values")
                continue

            for j in range(len(rows[i])):
                k = rows[i][j].text
                mission_dict[k] = \
                    self._parse_mission_cell_to_string(rows[i+1][j])
                if not mission_dict[k] \
                        or mission_dict[k] == "None" \
                        or mission_dict[k] == "N/A":
                    del mission_dict[k]

        return mission_dict

    def _parse_mission_cell_to_string(self, mission_cell):
        text = html.tostring(mission_cell).decode('utf-8')
        # Remove outer td, because we'll be adding our own later.
        text = re.sub(r'<td[^>]*>(.*)</td>', r'\1', text)
        # Put everything on one line for easy analysis later.
        text = re.sub(r'\n', r'', text)
        # Strip out all custom styling. (Use classes, dammit!)
        text = re.sub(r' style=[^>]*>', r'>', text)
        # Remove strong and p tags. We'll do our styling with CSS, thanks.
        text = re.sub(r'</?strong>', r'', text)
        text = re.sub(r'</?p>', r'', text)
        # Replace 3DS and Switch logo img tags with text-only spans.
        # We can style those spans later to make the text stand out.
        text = re.sub(r'<img [^>]*src="[^"]*/73095-150\.png"[^>]*>',
                      r'<span class="system-3ds">3DS:</span>', text)
        text = re.sub(r'<img [^>]*src="[^"]*/73095-151\.png"[^>]*>',
                      r'<span class="system-switch">Switch:</span>', text)
        # Remove all helper images. Detrimental for main adventure map,
        # but I don't want any calls to GameFAQs after the initial download.
        text = re.sub(r'<img [^>]*>', r'', text)
        # Remove all "opens this cell" links. The text is sufficient.
        text = re.sub(r'</?a[^>]*>', r'', text)
        # Remove any starting-text <br>'s. These happen because we got rid
        # of the helper images above.
        text = re.sub(r'^<br>', r'', text)

        return text

    def _write_interactive_html(self, all_page_dicts):
        with open(INT_HTML_FILE_NAME, 'w') as f:
            f.write(
                '<!doctype html>\n<html>\n<head>\n'
                '<script src="main.js"></script>\n'
                '<link href="main.css" rel="stylesheet" type="text/css">\n'
                '</head>\n<body>\n')
            f.write(
                '<h1>Hyrule Warriors Maps</h1>\n'
                '<h2>Notes</h2>\n')
            f.write(
                '<p>The data is scraped from <a href="'
                'https://gamefaqs.gamespot.com/switch/'
                '230454-hyrule-warriors-definitive-edition/faqs/73095">'
                'SBAllen\'s HW FAQ</a>. The code for the scraper is <a href="'
                'https://github.com/ibbmarsh/hyrule_warriors_maps">here</a>.'
                '</p>\n')
            f.write(
                '<p>Due to the homogeneity of the A-Rank Time requirements, '
                'I have removed those to save on visual space. For almost '
                'all missions, 15 minutes is the requirement. For most '
                '"Defeat all Giant Bosses in time!" missions, the requirement '
                'is 7 minutes instead.</p>\n')
            f.write(
                '<p>To lock a specific mission details table, click on '
                'the cell. To unlock and view other details tables, click '
                'it again.</p>\n')
            f.write(
                '<p>Difficulty order:'
                '<span class="difficulty-indicator difficulty-0">lowest'
                '</span>-&gt;'
                '<span class="difficulty-indicator difficulty-1">2</span>-&gt;'
                '<span class="difficulty-indicator difficulty-2">3</span>-&gt;'
                '<span class="difficulty-indicator difficulty-3">4</span>-&gt;'
                '<span class="difficulty-indicator difficulty-4">5</span>-&gt;'
                '<span class="difficulty-indicator difficulty-5">6</span>-&gt;'
                '<span class="difficulty-indicator difficulty-6">highest'
                '</span></p>\n')
            for map_name in MAP_NAMES:
                print("Writing HTML for {}".format(map_name))
                self._convert_page_dict_to_inthtml(
                    map_name, all_page_dicts[map_name], f)
            f.write(
                '<div class="spacer">&nbsp;</div>\n'
                '</body>\n</html>')

    def _convert_page_dict_to_inthtml(self, name, page_dict, f):
        f.write('<h2>{}</h2>\n'.format(name))
        f.write('<table>\n<tbody>\n')

        for i in range(page_dict['size'][0]):
            f.write('<tr>\n')
            for j in range(page_dict['size'][1]):
                cell_loc = '{}-{}'.format(ALPHABET[j], i+1)
                if cell_loc not in page_dict:
                    f.write('<td></td>\n')
                    continue
                f.write('<td class="cell-loc difficulty-{}" '
                        'data-mission="{}-mission-{}">{}</td>\n'
                        .format(page_dict[cell_loc]['difficulty'],
                                MAP_NAME_TO_PATH[name], cell_loc, cell_loc))
            f.write('</tr>\n')

        f.write('</tbody>\n</table>\n')

        for i in range(page_dict['size'][0]):
            for j in range(page_dict['size'][1]):
                cell_loc = '{}-{}'.format(ALPHABET[j], i+1)
                if cell_loc not in page_dict:
                    continue
                f.write('<table class="mission-data" id="{}-mission-{}">\n'
                        .format(MAP_NAME_TO_PATH[name], cell_loc))
                f.write('<tbody>\n')
                mission_data = page_dict[cell_loc]['mission-data']
                for k in VALID_MISSION_HEADERS:
                    if k not in mission_data:
                        continue
                    f.write('<tr>\n<th>{}</th>\n<td>{}</td>\n</tr>\n'
                            .format(k, mission_data[k]))
                f.write('</tbody>\n</table>\n')


if __name__ == '__main__':
    d = Driver()
    d.run()
