from datetime import date
import requests
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
            response = requests.get(url, timeout=3)
            return response.status_code

        # check and update NodeFree link
        NodeFree_url = f"https://nodefree.org/dy/{year}/{month}/{year}{month}{day}.yaml"
        if check_url(NodeFree_url) == 200:
            content = re.sub("nodefree.org/dy/[0-9]{4}/[0-9]{2}/[0-9]{8}",
                             f"nodefree.org/dy/{year}/{month}/{year}{month}{day}", content)

        # check and update ClashNode link
        ClashNode_url = f"https://clashnode.com/wp-content/uploads/{year}/{month}/{year}{month}{day}.yaml"
        if check_url(ClashNode_url) == 200:
            content = re.sub("clashnode.com/wp-content/uploads/[0-9]{4}/[0-9]{2}/[0-9]{8}",
                             f"clashnode.com/wp-content/uploads/{year}/{month}/{year}{month}{day}", content)

        # update Pojiezhiyuanjun link
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
