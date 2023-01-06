from datetime import date
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
        # update NodeFree link
        new_content = re.sub("[0-9]{4}/[0-9]{2}/[0-9]{8}\.yaml", f"{year}/{month}/{year}{month}{day}.yaml", content)
        # update Pojiezhiyuanjun link
        new_content = re.sub("[0-9]{4}clash\.yml", f"{month}{day}clash.yml", new_content)

        # open text file
        new_file = open(filename, "w")
        new_file.write(new_content)
        new_file.close()


if __name__ == "__main__":
    update("README.md")
    update("中文版.md")
