def compute_metrics(auto_results, human_labels):
    tp = fp = fn = tn = 0
    for auto_pass, human_pass in zip(auto_results, human_labels):
        if not auto_pass and not human_pass:
            tp += 1
        elif not auto_pass and human_pass:
            fp += 1
        elif auto_pass and not human_pass:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    n = len(auto_results)

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "n": n,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }
