

def ppstructure_analysis(input_path: str):
    img = cv2.imread(input_path)
    structure_engine = PPStructure(table=False, ocr=False, show_log=False)
    result = structure_engine(img)
    return result


def parse_range(page_range: str, is_multiple: bool = False):
    # e.g.: "1-3,5-6,7-10", "1,4-5"
    page_range = page_range.strip()
    parts = page_range.split(",")
    roi_indices = []
    for part in parts:
        out = list(map(int, part.split("-")))
        if len(out) == 2:
            roi_indices.append(list(range(out[0]-1, out[1])))
        elif len(out) == 1:
            roi_indices.append([out[0]-1])
    if is_multiple:
        return roi_indices
    result = [j for i in roi_indices for j in i]
    return result
