from datetime import date, datetime, timedelta, timezone
import requests
import json
import re


# update links in parameter file
def update(filename):
    with open(filename) as file:
        # get today's date
        today = date.today()
        year = today.strftime("%Y")
        month = today.strftime("%m")
        day = today.strftime("%d")

        # convert file to string
        content = file.read()

        # check url validity
        def check_url(url):
            try:
                response = requests.get(url, timeout=3)
            except requests.exceptions.ReadTimeout:
                return 504
            return response.status_code

        types = ["yaml", "txt"]
        for tp in types:
            # check and update NodeFree link
            NodeFree_url = f"https://nodefree.org/dy/{year}/{month}/{year}{month}{day}.{tp}"
            if check_url(NodeFree_url) == 200:
                content = re.sub("nodefree.org/dy/[0-9]{4}/[0-9]{2}/[0-9]{8}" + f".{tp}",
                                 f"nodefree.org/dy/{year}/{month}/{year}{month}{day}.{tp}", content)

            # check and update ClashNode link
            ClashNode_url = f"https://clashnode.com/wp-content/uploads/{year}/{month}/{year}{month}{day}.{tp}"
            if check_url(ClashNode_url) == 200:
                content = re.sub("clashnode.com/wp-content/uploads/[0-9]{4}/[0-9]{2}/[0-9]{8}" + f".{tp}",
                                 f"clashnode.com/wp-content/uploads/{year}/{month}/{year}{month}{day}.{tp}", content)

        def is_commit_recent(user, repo):
            response = requests.get(f'https://api.github.com/repos/{user}/{repo}/commits')
            data = json.loads(response.text)
            if response.status_code == 200 and data:
                commit_time = datetime.strptime(data[0]['commit']['committer']['date'], "%Y-%m-%dT%H:%M:%SZ")
                commit_time = commit_time.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if now - commit_time <= timedelta(hours=8):
                    return True

            return False

        # update Pojiezhiyuanjun link
        if is_commit_recent("Pojiezhiyuanjun", "2023"):
            content = re.sub("[0-9]{4}clash\.yml", f"{month}{day}clash.yml", content)
            content = re.sub("[0-9]{4}\.txt", f"{month}{day}.txt", content)

        # open text file
        new_file = open(filename, "w")
        new_file.write(content)
        new_file.close()


if __name__ == "__main__":
    update("README.md")
    update("v2ray.md")
    update("clash中文版.md")
    update("v2ray中文版.md")
    update("combine/clashsub.txt")
    update("combine/v2raysub.txt")
