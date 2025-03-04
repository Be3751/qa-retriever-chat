from markitdown import MarkItDown
import os

md = MarkItDown()
input_dir = os.path.join(os.path.dirname(__file__), "files/original")
output_dir = os.path.join(os.path.dirname(__file__), "files/markdown")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

for filename in os.listdir(input_dir):
    input_path = os.path.join(input_dir, filename)
    file_root, file_ext = os.path.splitext(filename)
    output_path = os.path.join(output_dir, file_root + ".md")
    
    result = md.convert(input_path)
    
    with open(output_path, "w") as output_file:
        output_file.write(result.text_content)