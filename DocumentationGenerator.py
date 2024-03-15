from tree_sitter import Language, Parser
import os

class DocumentationGenerator:
    ext_to_language_map = {}
    language_to_TSLanguage_map = {}
    
    def __init__(self, fileName, fileContents):
        self.fileName = fileName
        self.fileContents = fileContents
        _, ext = os.path.splitext(self.fileName)
        if ext not in self.ext_to_language_map: return
        language = self.ext_to_language_map[ext]
        self.tsLanguage = self.language_to_TSLanguage_map[language]
        self.parser = Parser()
        self.parser.set_language(self.tsLanguage)     
        self.tree = self.parser.parse(bytes(self.fileContents, "utf-8"))

    def query(self, query_string):
        query = self.tsLanguage.query(query_string)
        return query.matches(self.tree.root_node)

Language.build_library(
    "build/languages.so",
    ["treesitter/javascript", "treesitter/python"],
)

DocumentationGenerator.ext_to_language_map = {
    ".js": "javascript",
    ".py": "python"
}

DocumentationGenerator.language_to_TSLanguage_map = {
    "javascript": Language("build/languages.so", "javascript"),
    "python": Language("build/languages.so", "python")
}