import os

for filename in os.listdir("text"):
    if not filename.endswith(".tex"):
        continue

    with open(os.path.join("text", filename)) as file:
        data = file.read()

        # Convert image usages to use latex compatible formats.
        data = data.replace(".svg", ".pdf")

        # Pandoc generates figure environments with no positioning hints.
        # This doesn't usually result in desired output in user manual.
        # Add "h" option to place images near the intended location.
        data = data.replace(r"\begin{figure}", r"\begin{figure}[ht]")

    with open(os.path.join("text", filename), "w") as file:
        file.write(data)


