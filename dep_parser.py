import copy
import spacy
import re

class DepInstanceParser():
    def __init__(self, basicDependencies, tokens):
        self.basicDependencies = basicDependencies
        self.tokens = tokens
        self.words = []
        self.dep_governed_info = []
        self.dep_parsing()


    def dep_parsing(self):
        words = []
        for token in self.tokens:
            token['word'] = token['word'].replace('\xa0', '')
            words.append(self.change_word(token['word']))
        dep_governed_info = [
            {"word": word}
            for i,word in enumerate(words)
        ]
        for dep in self.basicDependencies:
            dependent_index = dep['dependent'] - 1
            governed_index = dep['governor'] - 1
            dep_governed_info[dependent_index] = {
                "governor": governed_index,
                "dep": dep['dep']
            }
        self.words = words
        self.dep_governed_info = dep_governed_info

    def change_word(self, word):
        if "-RRB-" in word:
            return word.replace("-RRB-", ")")
        if "-LRB-" in word:
            return word.replace("-LRB-", "(")
        return word

    def get_init_dep_matrix(self):
        dep_adj_matrix = [[0] * len(self.words) for _ in range(len(self.words))]
        dep_type_matrix = [["none"] * len(self.words) for _ in range(len(self.words))]
        for i in range(len(self.words)):
            dep_adj_matrix[i][i] = 1
            dep_type_matrix[i][i] = "self_loop"
        return dep_adj_matrix, dep_type_matrix

    def get_first_order(self, direct=False):
        dep_adj_matrix, dep_type_matrix = self.get_init_dep_matrix()

        for i, dep_info in enumerate(self.dep_governed_info):
            governor = dep_info["governor"]
            dep_type = dep_info["dep"]
            dep_adj_matrix[i][governor] = 1
            dep_adj_matrix[governor][i] = 1
            dep_type_matrix[i][governor] = dep_type if direct is False else "{}_in".format(dep_type)
            dep_type_matrix[governor][i] = dep_type if direct is False else "{}_out".format(dep_type)

        return dep_adj_matrix, dep_type_matrix

    def get_next_order(self, dep_adj_matrix, dep_type_matrix):
        new_dep_adj_matrix = copy.deepcopy(dep_adj_matrix)
        new_dep_type_matrix = copy.deepcopy(dep_type_matrix)
        for target_index in range(len(dep_adj_matrix)):
            for first_order_index in range(len(dep_adj_matrix[target_index])):
                if dep_adj_matrix[target_index][first_order_index] == 0:
                    continue
                for second_order_index in range(len(dep_adj_matrix[first_order_index])):
                    if dep_adj_matrix[first_order_index][second_order_index] == 0:
                        continue
                    if second_order_index == target_index:
                        continue
                    if new_dep_adj_matrix[target_index][second_order_index] == 1:
                        continue
                    new_dep_adj_matrix[target_index][second_order_index] = 1
                    new_dep_type_matrix[target_index][second_order_index] = dep_type_matrix[first_order_index][second_order_index]
        return new_dep_adj_matrix, new_dep_type_matrix

    def get_second_order(self, direct=False):
        dep_adj_matrix, dep_type_matrix = self.get_first_order(direct=direct)
        return self.get_next_order(dep_adj_matrix, dep_type_matrix)

    def get_third_order(self, direct=False):
        dep_adj_matrix, dep_type_matrix = self.get_second_order(direct=direct)
        return self.get_next_order(dep_adj_matrix, dep_type_matrix)

    def search_dep_path(self, start_idx, end_idx, adj_max, dep_path_arr):
        for next_id in range(len(adj_max[start_idx])):
            if next_id in dep_path_arr or adj_max[start_idx][next_id] in ["none"]:
                continue
            if next_id == end_idx:
                return 1, dep_path_arr + [next_id]
            stat, dep_arr = self.search_dep_path(next_id, end_idx, adj_max, dep_path_arr + [next_id])
            if stat == 1:
                return stat, dep_arr
        return 0, []

    def get_dep_path(self, start_range, end_range, direct=False):
        dep_path_adj_matrix, dep_path_type_matrix = self.get_init_dep_matrix()

        first_order_dep_adj_matrix, first_order_dep_type_matrix = self.get_first_order(direct=direct)
        for start_index in start_range:
            for end_index in end_range:
                _, dep_path_indexs = self.search_dep_path(start_index, end_index, first_order_dep_type_matrix, [start_index])
                for left_index, right_index in zip(dep_path_indexs[:-1], dep_path_indexs[1:]):
                    dep_path_adj_matrix[start_index][right_index] = 1
                    dep_path_type_matrix[start_index][right_index] = first_order_dep_type_matrix[left_index][right_index]
                    dep_path_adj_matrix[end_index][left_index] = 1
                    dep_path_type_matrix[end_index][left_index] = first_order_dep_type_matrix[right_index][left_index]
        return dep_path_adj_matrix, dep_path_type_matrix


class DepTreeParser():
    def __init__(self):
        pass

    def parsing(self, sentence):
        pass

class SpaCyDepTreeParser(DepTreeParser):
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def parsing(self, sentence):
        doc = self.nlp(sentence)
        basicDependencies = []
        tokens = []
        for i, token in enumerate(doc):
            if token.dep_ == "ROOT":
                basicDependencies.append({
                    "dep": token.dep_,
                    "governor": 0,
                    "governorGloss": "ROOT",
                    "dependent": token.i+1,
                    "dependentGloss": token.text
                })
            else:
                basicDependencies.append({
                    "dep": token.dep_,
                    "governor": token.head.i+1,
                    "governorGloss": token.head.text,
                    "dependent": token.i+1,
                    "dependentGloss": token.text
                })
            tokens.append({
                "index": token.i,
                "word": token.text,
                "originalText": token.text
            })
        return {
            "sentences": [
                {
                    "index": 0,
                    "line": 1,
                    "basicDependencies": basicDependencies,
                    "tokens": tokens
                }
            ]
        }

def test():
    import sys
    import json
    tsvfile = sys.argv[1]
    with open(tsvfile, 'r') as f:
        for line in f:
            ins = json.loads(line.strip())
            for sentence in ins["sentences"]:
                dep_instance_parser = DepInstanceParser(basicDependencies=sentence["basicDependencies"],
                                                        tokens=sentence["tokens"])
                tokens = dep_instance_parser.words
                print(" ".join(tokens))
                print("first order dep")
                dep_adj_matrix, dep_type_matrix = dep_instance_parser.get_first_order()
                for i in range(len(dep_type_matrix)):
                    token = tokens[i]
                    adj_range = [index for index in range(len(dep_adj_matrix[i])) if dep_adj_matrix[i][index] == 1]
                    keys = ",".join([tokens[index] for index in adj_range])
                    values = ",".join([dep_type_matrix[i][index] for index in adj_range])
                    print("#{} keys: {}, values: {}".format(token, keys, values))
                print("second order dep")
                dep_adj_matrix, dep_type_matrix = dep_instance_parser.get_second_order()
                for i in range(len(dep_type_matrix)):
                    token = tokens[i]
                    adj_range = [index for index in range(len(dep_adj_matrix[i])) if dep_adj_matrix[i][index] == 1]
                    keys = ",".join([tokens[index] for index in adj_range])
                    values = ",".join([dep_type_matrix[i][index] for index in adj_range])
                    print("#{} keys: {}, values: {}".format(token, keys, values))
                print("third order dep")
                dep_adj_matrix, dep_type_matrix = dep_instance_parser.get_third_order()
                for i in range(len(dep_type_matrix)):
                    token = tokens[i]
                    adj_range = [index for index in range(len(dep_adj_matrix[i])) if dep_adj_matrix[i][index] == 1]
                    keys = ",".join([tokens[index] for index in adj_range])
                    values = ",".join([dep_type_matrix[i][index] for index in adj_range])
                    print("#{} keys: {}, values: {}".format(token, keys, values))
                print("dep path")
                dep_adj_matrix, dep_type_matrix = dep_instance_parser.get_dep_path([1], [5, 6])
                for i in range(len(dep_type_matrix)):
                    token = tokens[i]
                    adj_range = [index for index in range(len(dep_adj_matrix[i])) if dep_adj_matrix[i][index] == 1]
                    keys = ",".join([tokens[index] for index in adj_range])
                    values = ",".join([dep_type_matrix[i][index] for index in adj_range])
                    print("#{} keys: {}, values: {}".format(token, keys, values))
            exit()

def test_spacy_tree_parsing():
    import sys
    import json
    tsvfile = sys.argv[1]
    savfile = sys.argv[2]
    spacy_tool = SpaCyDepTreeParser()
    with open(tsvfile, 'r') as fin, open(savfile, 'w') as fout:
        lines = fin.readlines()
        for line in lines:
            line = line.replace("<e1> </e1>", "<e1> # </e1>").replace("<e2> </e2>", "<e2> # </e2>")
            splits = line.split('\t')
            if len(splits) < 1:
                continue
            e1, e2, label, sentence = splits
            sentence = sentence.strip()

            def text_filter(s):
                s = re.sub(r'(https|http)?:\/\/(\w|\.|\/|\?|\=|\&|\%)*\b', '', s, flags=re.MULTILINE)
                s = re.sub(r'\[ image : (\w|\.|\/|\?|\=|\&|\%)*\b \]', '', s, flags=re.MULTILINE)
                re.sub(r'--', '', s, flags=re.MULTILINE)
                return s

            if sentence != text_filter(sentence):
                print(sentence+"\n")
                print(text_filter(sentence)+"\n")
            sentence = text_filter(sentence)
            ori_sentence = " ".join(re.split("(<e1>|<e2>|</e1>|</e2>)", sentence)).split(" ")
            words = [s for s in ori_sentence if s not in ["<e1>", "</e1>", "<e2>", "</e2>"]]
            result = spacy_tool.parsing(" ".join(words))
            result["e1"] = e1
            result["e2"] = e2
            result["label"] = label
            result["raw_sentence"] = sentence
            result["ori_sentence"] = ori_sentence
            result["word"] = words
            fout.write("{}\n".format(json.dumps(result)))

if __name__ == "__main__":
    # test()
    test_spacy_tree_parsing()