import requests
import warnings
import datetime
import re
import json

from lxml import html

def get_security_releases():
    response = requests.get("https://support.apple.com/en-us/HT201222")
    return response.text

def parse_data(data):
    # xpath //*[@id="tableWraper"]/table/tbody
    tree = html.fromstring(data)
    all_versions = tree.xpath('//*[@id="tableWraper"]/table/tbody/tr')

    versions = []
    for idx, version in enumerate(all_versions):
        version_data = version.xpath('td')

        if version_data == []:
            continue
        
        if len(version_data) != 3:
            warnings.warn("The HTML structure has changed for row: {}".format(idx))

        # parse release date to datetime
        try:
            release_date = datetime.datetime.strptime(version_data[2].text, "%d %b %Y")
        except ValueError:
            continue        

        output = {
            "name": version_data[0].text_content().split("\n")[0].strip().replace('\u00a0', ' '),
            "available_for": version_data[1].text,
            "release_date": release_date
        }

        if version_data[0].xpath('a'):
            output["security_updates_url"] = version_data[0].xpath('a')[0].attrib["href"]

        versions.append(output)



    return versions


if __name__ == "__main__":
    security_releases_html = get_security_releases()

    # Parse the data
    all_versions = parse_data(security_releases_html)

    # Only include the versions that are available for macOS
    mac_versions = [version for version in all_versions if version["name"].startswith("macOS") and "server" not in version["name"].lower()]

    # Reverse the list so the oldest version is first
    mac_versions.reverse()

    versions = {}

    # Iterate through collating supplemantal version updates
    for version in mac_versions:
        # regex out the version number
        try:
            version_number = re.search(r'\d+(\.\d+)?(\.\d+)?', version["name"]).group()
        except AttributeError:
            print("No version number found for: {}".format(version["name"]))

        # Normalize the version number to x.x.x 
        if version_number.count(".") == 1:
            version_number += ".0"
        elif version_number.count(".") == 0:
            version_number += ".0.0"
        

        if version_number not in versions:
            versions[version_number] = {
                "name": version["name"],
                "release_date": version["release_date"],
                "security_updates_url": version.get("security_updates_url"),
                "supplemental_updates": []
            }
        else:
            versions[version_number]["supplemental_updates"].append({
                "name": version["name"],
                "release_date": version["release_date"],
                "security_updates_url": version.get("security_updates_url")
            })

    version_keys = sorted(list(versions.keys()), reverse=True)
    last_3_major_versions = sorted(set([version.split(".")[0] for version in version_keys]), reverse=True)[:3]

    # For each major version, find the latest release
    latest_major_versions = {}

    for major_version in last_3_major_versions:
        for version in version_keys:
            if version.startswith(major_version):
                versions[version]["latest"] = True
                break

    # Add an unsupported tag to versions outside of the last 3 major versions
    for version in version_keys:
        if version.split(".")[0] not in last_3_major_versions:
            versions[version]["unsupported"] = True

    versions_by_release_date = dict(sorted(versions.items(), key=lambda x: x[1]["release_date"], reverse=True))

    with open("macos_versions_by_release_date.json", "w") as f:
        json.dump(versions_by_release_date, f, indent=4, default=str)

    print("Output written to macos_versions_by_release_date.json")

    versions_by_version_number = dict(sorted(versions.items(), key=lambda x: x[0], reverse=True))

    with open("macos_versions_by_version_number.json", "w") as f:
        json.dump(versions_by_version_number, f, indent=4, default=str)

    print("Output written to macos_versions_by_version_number.json")

