import os


def count_vocab_size(dictionary, modalities):
    # TODO: check tokens filtered by dict.filter()
    fname = 'tmp.txt'
    try:
        dictionary.save_text(fname)
        modality_count = {name: 0 for name in modalities}
        modality_vocab_size = {name: 0 for name in modalities}
        with open(fname) as f:
            header = next(f)
            num_docs = int(header.partition("num_items: ")[2])
            next(f)
            for line in f:
                token, class_id, _, token_tf, token_df = line.split(", ")
                if class_id in modalities:
                    modality_count[class_id] += float(token_tf)
                    modality_vocab_size[class_id] += 1
        return (modality_count, modality_vocab_size, num_docs)
    finally:
        os.remove(fname)


def calc_docs_avg_len(ds, weights):
    (modality_count, modality_vocab_size, n_docs) = ds
    docs_total_len = 0
    for modality, tokens_total_sum in modality_count.items():
        w = weights[modality]
        docs_total_len += w * tokens_total_sum
    avg_doc_len = docs_total_len / n_docs
    return avg_doc_len


def theta_weight_abs2rel(ds, modality_weights, n_topics, tau):
    avg_doc_len = calc_docs_avg_len(ds, modality_weights)
    gimel_multiplier = avg_doc_len / n_topics + tau
    gimel = tau / gimel_multiplier
    return gimel


def theta_weight_rel2abs(ds, modality_weights, n_topics, gimel):
    avg_doc_len = calc_docs_avg_len(ds, modality_weights)
    tau = (avg_doc_len / n_topics) * gimel / (1 - gimel)
    return tau


def phi_weight_abs2rel(ds, modality_weights, n_topics, tau, modalities_list=None):
    (modality_count, modality_vocab_size, n_docs) = ds
    if modalities_list is None:
        modalities_list = modality_count.keys()
    docs_total_len = 0
    vocab_size = 0
    for modality in modalities_list:
        tokens_total_sum = modality_count[modality]
        vocab_size += modality_vocab_size[modality]
        w = modality_weights[modality]
        docs_total_len += w * tokens_total_sum
    # TODO: check if formula is OK
    odds_gimel = (tau * n_topics * vocab_size) / docs_total_len
    gimel = odds_gimel / (1 + odds_gimel)
    return gimel


def phi_weight_rel2abs(ds, modality_weights, n_topics, gimel, modalities_list=None):
    (modality_count, modality_vocab_size, n_docs) = ds
    if modalities_list is None:
        modalities_list = modality_count.keys()
    docs_total_len = 0
    vocab_size = 0
    for modality in modalities_list:
        tokens_total_sum = modality_count[modality]
        vocab_size += modality_vocab_size[modality]
        w = modality_weights[modality]
        docs_total_len += w * tokens_total_sum
    # TODO: check if formula is OK
    tau = (docs_total_len / (n_topics * vocab_size)) * gimel / (1 - gimel)
    return tau


def compute_regularizer_tau(tokens_data, reg, modality_weights):

    (modality_count, modality_vocab_size, num_docs) = tokens_data

    if isinstance(reg.tau, str) and "rel" == reg.tau[-3:]:
        gimel = float(reg.tau[:-3])
    else:
        return reg.tau

    if "SmoothSparseThetaRegularizer" in str(type(reg)):
        tau = theta_weight_rel2abs(tokens_data, modality_weights,
                                   len(reg.topic_names), gimel)
        return tau
    elif "SmoothSparsePhiRegularizer" in str(type(reg)):
        if len(reg.class_ids):
            modalities_list = reg.class_ids
        else:
            modalities_list = modality_weights.keys()

        tau = phi_weight_rel2abs(tokens_data, modality_weights,
                                 len(reg.topic_names), gimel, modalities_list)
        return tau
    elif "DecorrelatorPhiRegularizer" in str(type(reg)):
        raise ValueError("Decorrelator {} warrants further study".format(reg.name))
    else:
        raise KeyError("Invalid: {}".format(reg.name))


def compute_regularizer_gimel(tokens_data, reg, modality_weights):

    (modality_count, modality_vocab_size, num_docs) = tokens_data

    if "SmoothSparseThetaRegularizer" in str(type(reg)):
        gimel = theta_weight_abs2rel(tokens_data, modality_weights,
                                     len(reg.topic_names), reg.tau)
        return gimel
    elif "SmoothSparsePhiRegularizer" in str(type(reg)):
        if len(reg.class_ids):
            modalities_list = reg.class_ids
        else:
            modalities_list = modality_weights.keys()

        gimel = phi_weight_abs2rel(tokens_data, modality_weights,
                                   len(reg.topic_names), reg.tau, modalities_list)
        return gimel
    elif "DecorrelatorPhiRegularizer" in str(type(reg)):
        raise ValueError("Decorrelator {} warrants further study".format(reg.name))
    else:
        raise KeyError("Invalid: {}".format(reg.name))


def transform_regularizer(tokens_data, reg, modality_weights):

    (modality_count, modality_vocab_size, num_docs) = tokens_data

    new_tau = compute_regularizer_tau(tokens_data, reg, modality_weights)
    reg_class = reg.__class__
    reg_copy = reg_class(
            tau=new_tau,
            name=reg.name,
            topic_names=reg.topic_names,
            # class_ids=reg.class_ids
    )
    return reg_copy


def modality_weight_rel2abs(tokens_data, weights, default_modality):
    (modality_count, modality_vocab_size, num_docs) = tokens_data
    taus = {}
    default_weight = modality_count[default_modality]
    for modality in weights:
        if modality_count[modality]:
            gimel = weights[modality]
            tau = gimel * default_weight / modality_count[modality]
            taus[modality] = tau
        else:
            taus[modality] = 0
    return taus