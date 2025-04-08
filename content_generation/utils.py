import re


def json_to_text(data):
    text = f"{data['Title']}\n\n"
    # text += f"Topic: {data['Topic']}\n\n"
    text += f" {data['Description']}\n\n"
    text += f"{data['Introduction']}\n\n"
    # text += "Sections:\n"
    for i, section in enumerate(data['Sections'], 1):
        text += f"  {i}. {section['Subheading']}\n"
        text += f"     {section['Content']}\n\n"
    text += f"{data['Conclusion']}"
    return text


def text_to_json(text):
    data = {}
    lines = text.split("\n")
    sections = []
    current_section = {}
    content_flag = False

    for line in lines:
        line = line.strip()
        if line.startswith("Title:"):
            data["Title"] = line.replace("Title:", "").strip()
        elif line.startswith("Topic:"):
            data["Topic"] = line.replace("Topic:", "").strip()
        elif line.startswith("Description:"):
            data["Description"] = line.replace("Description:", "").strip()
        elif line.startswith("Introduction:"):
            data["Introduction"] = line.replace("Introduction:", "").strip()
        elif line.startswith("Sections:"):
            continue
        elif re.match(r"\d+\.\s+Subheading:", line):
            if current_section:
                sections.append(current_section)
            current_section = {"Subheading": line.split("Subheading:")[1].strip()}
            content_flag = False
        elif line.startswith("Content:"):
            current_section["Content"] = line.replace("Content:", "").strip()
            content_flag = True
        elif content_flag and line:
            current_section["Content"] += "\n" + line.strip()
    
    if current_section:
        sections.append(current_section)
    
    data["Sections"] = sections
    data["Conclusion"] = lines[-1].replace("Conclusion:", "").strip() if lines[-1].startswith("Conclusion:") else ""
    
    return data


def clean_string(s):
    """
    Cleans up a string by stripping leading/trailing whitespace
    and removing unwanted trailing digits or slashes.
    """
    if s is None or not isinstance(s, str) or s.strip() == "":
        return None
    cleaned = s.strip().rstrip("0123456789/").strip()
    return cleaned
