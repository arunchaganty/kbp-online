from IPython.display import HTML, display

def to_table(data, cols=None):
    html = "<table>"
    _, ncols = len(data), len(data[0])
    if cols is None: cols = list(range(ncols))

    html += "<thead>"
    html += "<tr>"
    for col in cols:
        html += "<th>{}</th>".format(col)
    html += "</tr>"
    html += "</thead>"

    for row in data:
        html += "<tr>"
        for col in row:
            html += "<td>{}</td>".format(col)
        html += "</tr>"

    html += "</table>"
    return display(HTML(html))

