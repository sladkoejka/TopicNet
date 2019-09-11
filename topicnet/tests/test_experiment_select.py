import artm
from itertools import combinations
from itertools import product
import numpy as np
import shutil
import tempfile

import pytest

from ..cooking_machine.models.topic_model import TopicModel
from ..cooking_machine.experiment import Experiment


ARTM_MODEL = artm.ARTM(num_topics=1, num_processors=1)


SCORES = ['PerplexityScore', 'SparsityPhiScore']
INIT_PARAMETERS = ['num_topics', 'num_document_passes']


AND = 'and'
MAX = 'max'
MIN = 'min'
ARROW_TO = '->'
LESS = '<'
GREATER = '>'
EQUALS = '='

CONSTRAINT_LESS_THAN = f'{{0}} {LESS} {{1}}'
CONSTRAINT_EQUALS_TO = f'{{0}} {EQUALS} {{1}}'
CONSTRAINT_GREATER_THAN = f'{{0}} {GREATER} {{1}}'
CONSTRAINT_MAXIMIZE = f'{{0}} {ARROW_TO} {MAX}'
CONSTRAINT_MINIMIZE = f'{{0}} {ARROW_TO} {MIN}'

INIT_PARAMETER_PREFIX = 'model.'


MIN_SCORE = -0.2  # seems better to use floats right away (without ints)
MAX_SCORE = +0.3
SCORE_STEP = 0.1
SCORE_RANGE = np.arange(MIN_SCORE, MAX_SCORE + SCORE_STEP, SCORE_STEP)
MIDDLE_SCORE = int((MAX_SCORE + MIN_SCORE) / 2)

MIN_INIT_PARAMETER = -0.2
MAX_INIT_PARAMETER = +0.3
INIT_PARAMETER_STEP = 0.1
INIT_PARAMETER_RANGE = np.arange(
    MIN_INIT_PARAMETER, MAX_INIT_PARAMETER + INIT_PARAMETER_STEP, INIT_PARAMETER_STEP
)
MIDDLE_INIT_PARAMETER = int((MAX_INIT_PARAMETER + MIN_INIT_PARAMETER) / 2)


LEVELS_INVALID_TYPE = ['INVALID_LEVEL', -17.5]
NUM_MODELS_INVALID_TYPE = 'INVALID_NUM_MODELS'
NUM_MODELS_INVALID_VALUE = -1


def format_score(score):
    return score


def format_init_parameter(init_parameter):
    return INIT_PARAMETER_PREFIX + init_parameter


def combine_constraints(*constraints, connector=AND, symbol_before=' ', symbol_after=' '):
    return f'{symbol_before}{connector}{symbol_after}'.join(constraints)


class MockTopicModel(TopicModel):
    def __init__(self, name, depth=1):
        super().__init__(model_id=name, artm_model=ARTM_MODEL)

        self._name = name
        self._depth = depth
        self._scores = dict()
        self._init_parameters = dict()

    @property
    def depth(self):
        return self._depth

    @property
    def scores(self):
        return self._scores

    @property
    def init_parameters(self):
        return self._init_parameters

    @property
    def name(self):
        return self._name

    def __str__(self):
        # Trying to gather all the info so as not to log during tests
        result = f'{self._name}'

        for s, v in self.scores.items():
            result += f'__s:{s}:{v[-1]:.2f}'

        for p, v in self.init_parameters.items():
            result += f'__p:{p}:{v:.2f}'

        return result

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        if other is None:
            return False

        if not isinstance(other, MockTopicModel):
            return False

        if self.__hash__() != other.__hash__():
            return False

        return True

    def get_init_parameters(self):
        return self._init_parameters

    def set_init_parameter(self, name: str, value):
        self._init_parameters[name] = value

        return self

    def set_score(self, name: str, values: list):
        assert isinstance(name, str) and len(name) > 0
        assert isinstance(values, list)

        self._scores[name] = values

        return self

    @staticmethod
    def generate_specified_models(scores_ranges: dict = None, init_parameters_ranges: dict = None):
        def get_all_names_all_ranges_and_model_id_prefix():
            nonlocal scores_ranges
            nonlocal init_parameters_ranges

            if scores_ranges is not None and init_parameters_ranges is not None:
                return (
                    list(scores_ranges.keys()) + list(init_parameters_ranges.keys()),
                    list(scores_ranges.values()) + list(init_parameters_ranges.values()),
                    'm_sp_'
                )
            elif scores_ranges is None:
                return (
                    list(init_parameters_ranges.keys()),
                    list(init_parameters_ranges.values()),
                    'm_p_'
                )
            else:  # init_parameters_ranges is None
                return (
                    list(scores_ranges.keys()),
                    list(scores_ranges.values()),
                    'm_s_'
                )

        if scores_ranges is None:
            scores_ranges = dict()
        if init_parameters_ranges is None:
            init_parameters_ranges = dict()

        scores_names = set(scores_ranges.keys())
        names, ranges, model_id_prefix = get_all_names_all_ranges_and_model_id_prefix()
        models = []

        for ranges_section in product(*ranges):
            model = MockTopicModel(name=f'{model_id_prefix}{len(models):04}')

            for name, value in zip(names, ranges_section):
                if name in scores_names:
                    model.set_score(name, [value])
                else:
                    model.set_init_parameter(name, value)

            models.append(model)

        return models


def get_models(
        scores: list = None, init_parameters: list = None,
        score_range=None, init_parameters_range=None):

    scores_ranges = {
        s: score_range or SCORE_RANGE for s in scores
    } if scores is not None else None

    init_parameters_ranges = {
        p: init_parameters_range or INIT_PARAMETER_RANGE for p in init_parameters
    } if init_parameters is not None else None

    return MockTopicModel.generate_specified_models(
        scores_ranges=scores_ranges,
        init_parameters_ranges=init_parameters_ranges
    )


def get_models_with_two_scores_two_init_parameters():
    score_start_index = np.random.randint(0, len(SCORES) - 1)
    scores = SCORES[score_start_index:score_start_index + 2]

    init_parameter_start_index = np.random.randint(0, len(INIT_PARAMETERS) - 1)
    init_parameters = INIT_PARAMETERS[init_parameter_start_index:init_parameter_start_index + 2]

    assert len(scores) == 2
    assert len(init_parameters) == 2

    return get_models(scores=scores, init_parameters=init_parameters)


def get_models_with_one_score(score=None):
    if score is not None:
        return get_models(scores=[score])

    score_index = np.random.randint(0, len(SCORES))

    return get_models(scores=[SCORES[score_index]])


def get_models_with_one_init_parameter(init_parameter=None):
    if init_parameter is not None:
        return get_models(init_parameters=[init_parameter])

    init_parameter_index = np.random.randint(0, len(INIT_PARAMETERS))

    return get_models(init_parameters=[INIT_PARAMETERS[init_parameter_index]])


class TestExperimentSelect:
    experiments_folder = None
    current_experiment_id = -1
    query_sample = None

    @classmethod
    def setup_class(cls):
        cls.experiments_folder = tempfile.mkdtemp()
        cls.query_sample = CONSTRAINT_MAXIMIZE.format(format_score(SCORES[0]))

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.experiments_folder)

    @staticmethod
    def get_experiment(with_models=True):
        TestExperimentSelect.current_experiment_id += 1

        experiment = Experiment(
            experiment_id=f'{TestExperimentSelect.current_experiment_id:03}',
            save_path=TestExperimentSelect.experiments_folder)

        if with_models:
            TestExperimentSelect.set_models(
                experiment,
                get_models_with_two_scores_two_init_parameters()
            )

        return experiment

    @staticmethod
    def set_models(experiment, models):
        # without erasing experiment.models: "start model" stays
        experiment.models.update(
            {m.name: m for m in models}
        )

    @staticmethod
    def get_filter_for_score(query, score, threshold, models):
        if f'{ARROW_TO} {MAX}' in query:
            return lambda m: m.scores[score][-1] == max(
                model.scores[score][-1] for model in models if score in model.scores)\
                if score in m.scores else False
        if f'{ARROW_TO} {MIN}' in query:
            return lambda m: m.scores[score][-1] == min(
                model.scores[score][-1] for model in models if score in model.scores)\
                if score in m.scores else False
        if LESS in query:
            return lambda m: m.scores[score][-1] < threshold\
                if score in m.scores else False
        if EQUALS in query:
            return lambda m: m.scores[score][-1] == threshold\
                if score in m.scores else False
        if GREATER in query:
            return lambda m: m.scores[score][-1] > threshold\
                if score in m.scores else False

        raise ValueError(
            f'Don\'t know what to do with query "{query}" for score "{score}"...')

    @staticmethod
    def get_filter_for_init_parameter(query, parameter, threshold):
        # First "start" model is BaseModel and don't have get_init_parameters()
        # so need isinstance() check
        if LESS in query:
            return lambda m: m.get_init_parameters().get(parameter) < threshold\
                if isinstance(m, TopicModel) and parameter in m.get_init_parameters() else False
        if EQUALS in query:
            return lambda m: m.get_init_parameters().get(parameter) == threshold \
                if isinstance(m, TopicModel) and parameter in m.get_init_parameters() else False
        if GREATER in query:
            return lambda m: m.get_init_parameters().get(parameter) > threshold \
                if isinstance(m, TopicModel) and parameter in m.get_init_parameters() else False

        raise ValueError(
            f'Don\'t know what to do with query "{query}" for init parameter "{parameter}"...')

    @pytest.mark.xfail
    @pytest.mark.parametrize('level', LEVELS_INVALID_TYPE)
    def test_invalid_level_without_models(self, level):
        experiment = TestExperimentSelect.get_experiment(with_models=False)

        selection = experiment.select(TestExperimentSelect.query_sample, level=level)

        # TODO: or better also throw error as with models?
        assert len(selection) == 0, 'Some models selected with invalid "level"'

    @pytest.mark.xfail
    @pytest.mark.parametrize('level', LEVELS_INVALID_TYPE)
    def test_invalid_level_with_models(self, level):
        experiment = TestExperimentSelect.get_experiment()

        with pytest.raises(TypeError):
            _ = experiment.select(TestExperimentSelect.query_sample, level=level)

    @pytest.mark.xfail
    def test_invalid_num_models_without_models(self):
        experiment = TestExperimentSelect.get_experiment(with_models=False)

        selection = experiment.select(
            TestExperimentSelect.query_sample, models_num=NUM_MODELS_INVALID_TYPE
        )

        # TODO: or better also throw error as with models?
        assert len(selection) == 0, 'Some models selected with invalid "models_num"'

    @pytest.mark.xfail
    def test_invalid_num_models_with_models(self):
        experiment = TestExperimentSelect.get_experiment()

        with pytest.raises(TypeError):
            _ = experiment.select(
                TestExperimentSelect.query_sample, models_num=NUM_MODELS_INVALID_TYPE
            )

    @pytest.mark.xfail
    @pytest.mark.parametrize('with_models', [False, True])
    def test_zero_num_models(self, with_models):
        experiment = TestExperimentSelect.get_experiment(with_models=with_models)

        selection = experiment.select(TestExperimentSelect.query_sample, models_num=0)

        assert len(selection) == 0, 'Some models selected'

    @pytest.mark.xfail
    @pytest.mark.parametrize('with_models', [False, True])
    def test_wrong_num_models(self, with_models):
        experiment = TestExperimentSelect.get_experiment(with_models=with_models)

        with pytest.raises(ValueError):
            _ = experiment.select(
                TestExperimentSelect.query_sample, models_num=NUM_MODELS_INVALID_VALUE
            )

    def test_default_level(self):
        experiment = TestExperimentSelect.get_experiment()

        selection = experiment.select(TestExperimentSelect.query_sample)
        max_depth = max(m.depth for m in experiment.models.values())

        assert len(selection) > 0,\
            'None models selected'
        assert all(s.depth == max_depth for s in selection),\
            'Some models among selected have wrong depth'

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        'score, init_parameter, score_threshold, init_parameter_threshold',
        [(SCORES[0], INIT_PARAMETERS[0], MIDDLE_SCORE, MAX_INIT_PARAMETER)]
    )
    def test_default_num_models(
            self, score, init_parameter, score_threshold, init_parameter_threshold):

        experiment = TestExperimentSelect.get_experiment()

        selection_a = experiment.select(
            CONSTRAINT_MAXIMIZE.format(format_score(score))
        )
        selection_b = experiment.select(
            CONSTRAINT_GREATER_THAN.format(format_score(score), score_threshold)
        )
        selection_c = experiment.select(
            CONSTRAINT_LESS_THAN.format(
                format_init_parameter(init_parameter), init_parameter_threshold
            )
        )

        assert len(selection_a) == len(selection_b) == len(selection_c),\
            'Returns different number of models for different queries'

    @pytest.mark.parametrize(
        'score, threshold',
        [(SCORES[0], MIDDLE_SCORE)]
    )
    @pytest.mark.parametrize(
        'query_template',
        [CONSTRAINT_LESS_THAN, CONSTRAINT_EQUALS_TO, CONSTRAINT_GREATER_THAN,
         CONSTRAINT_MAXIMIZE, CONSTRAINT_MINIMIZE]
    )
    @pytest.mark.parametrize(
        'get_models_func',
        [get_models_with_two_scores_two_init_parameters,
         lambda: get_models_with_one_score(SCORES[0])]  # need to pass score, but call later
    )
    def test_select_by_score(self, score, threshold, query_template, get_models_func):
        # Need to find satisfying in test, because "models" is a class variable
        experiment = TestExperimentSelect.get_experiment(with_models=False)
        TestExperimentSelect.set_models(experiment, get_models_func())

        query = query_template.format(format_score(score), threshold)
        selection = experiment.select(query)

        filter_func = TestExperimentSelect.get_filter_for_score(
            query, score, threshold, experiment.models.values()
        )
        satisfying = list(filter(filter_func, experiment.models.values()))

        assert set(selection).issubset(set(satisfying)),\
            f'Some models among selected don\'t satisfy ' \
            f'the query "{query}"'

    @pytest.mark.parametrize(
        'init_parameter, threshold',
        [(INIT_PARAMETERS[0], MIDDLE_INIT_PARAMETER)]
    )
    @pytest.mark.parametrize(
        'query_template',
        [CONSTRAINT_LESS_THAN, CONSTRAINT_EQUALS_TO, CONSTRAINT_GREATER_THAN]
    )
    @pytest.mark.parametrize(
        'get_models_func',
        [get_models_with_two_scores_two_init_parameters,
         lambda: get_models_with_one_init_parameter(INIT_PARAMETERS[0])]
    )
    def test_select_by_parameter(self, init_parameter, threshold, query_template, get_models_func):
        experiment = TestExperimentSelect.get_experiment(with_models=False)
        TestExperimentSelect.set_models(experiment, get_models_func())

        query = query_template.format(format_init_parameter(init_parameter), threshold)
        selection = experiment.select(query)

        filter_func = TestExperimentSelect.get_filter_for_init_parameter(
            query, init_parameter, threshold
        )
        satisfying = list(filter(filter_func, experiment.models.values()))

        assert set(selection).issubset(set(satisfying)), \
            f'Some models among selected don\'t satisfy ' \
            f'the query "{query}"'

    @pytest.mark.parametrize(
        'constraint_a_template',
        [CONSTRAINT_LESS_THAN, CONSTRAINT_EQUALS_TO, CONSTRAINT_GREATER_THAN,
         CONSTRAINT_MAXIMIZE, CONSTRAINT_MINIMIZE]
    )
    @pytest.mark.parametrize(
        'constraint_b_template',
        [CONSTRAINT_LESS_THAN, CONSTRAINT_EQUALS_TO, CONSTRAINT_GREATER_THAN,
         CONSTRAINT_MAXIMIZE, CONSTRAINT_MINIMIZE]
    )
    @pytest.mark.parametrize(
        'score_a, threshold_a, score_b, threshold_b',
        [(SCORES[0], MIDDLE_SCORE, SCORES[1], MIDDLE_SCORE)]
    )
    def test_select_by_scores(
            self, constraint_a_template, constraint_b_template,
            score_a, threshold_a, score_b, threshold_b):

        experiment = TestExperimentSelect.get_experiment()

        constraint_a = constraint_a_template.format(format_score(score_a), threshold_a)
        constraint_b = constraint_b_template.format(format_score(score_b), threshold_b)
        query = combine_constraints(constraint_a, constraint_b)

        if ARROW_TO in constraint_a and ARROW_TO in constraint_b:
            # The case is not considered in this test
            return

        selection = experiment.select(query)

        filter_func_a = TestExperimentSelect.get_filter_for_score(
            constraint_a, score_a, threshold_a, experiment.models.values()
        )
        satisfying = list(filter(filter_func_a, experiment.models.values()))
        filter_func_b = TestExperimentSelect.get_filter_for_score(
            constraint_b, score_b, threshold_b, experiment.models.values()
        )
        satisfying = list(filter(filter_func_b, satisfying))

        assert set(selection).issubset(set(satisfying)), \
            f'Some models among selected don\'t satisfy ' \
            f'the query "{query}"'

    @pytest.mark.parametrize(
        'constraint_a_template', [CONSTRAINT_MAXIMIZE, CONSTRAINT_MINIMIZE]
    )
    @pytest.mark.parametrize(
        'constraint_b_template', [CONSTRAINT_MAXIMIZE, CONSTRAINT_MINIMIZE]
    )
    @pytest.mark.parametrize(
        'score_a, score_b', [(SCORES[0], SCORES[1])]
    )
    def test_two_optimizations(
            self, constraint_a_template, constraint_b_template, score_a, score_b):

        experiment = TestExperimentSelect.get_experiment()

        optimization_a = constraint_a_template.format(format_score(score_a))
        optimization_b = constraint_b_template.format(format_score(score_b))
        query = combine_constraints(optimization_a, optimization_b)

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.parametrize(
        'constraint_a_template',
        [CONSTRAINT_LESS_THAN, CONSTRAINT_EQUALS_TO, CONSTRAINT_GREATER_THAN]
    )
    @pytest.mark.parametrize(
        'constraint_b_template',
        [CONSTRAINT_LESS_THAN, CONSTRAINT_EQUALS_TO, CONSTRAINT_GREATER_THAN]
    )
    @pytest.mark.parametrize(
        'init_parameter_a, threshold_a, init_parameter_b, threshold_b',
        [(INIT_PARAMETERS[0], MIDDLE_INIT_PARAMETER, INIT_PARAMETERS[1], MIDDLE_INIT_PARAMETER)]
    )
    def test_select_by_init_parameters(
            self, constraint_a_template, constraint_b_template,
            init_parameter_a, threshold_a, init_parameter_b, threshold_b):

        experiment = TestExperimentSelect.get_experiment()

        constraint_a = constraint_a_template.format(
            format_init_parameter(init_parameter_a), threshold_a)
        constraint_b = constraint_a_template.format(
            format_init_parameter(init_parameter_b), threshold_b)
        query = combine_constraints(constraint_a, constraint_b)
        selection = experiment.select(query)

        filter_func_a = TestExperimentSelect.get_filter_for_init_parameter(
            constraint_a, init_parameter_a, threshold_a
        )
        satisfying = list(filter(filter_func_a, experiment.models.values()))
        filter_func_b = TestExperimentSelect.get_filter_for_init_parameter(
            constraint_b, init_parameter_b, threshold_b
        )
        satisfying = list(filter(filter_func_b, satisfying))

        assert set(selection).issubset(set(satisfying)), \
            f'Some models among selected don\'t satisfy ' \
            f'the query "{query}"'

    @pytest.mark.parametrize(
        'constraint_score_template',
        [CONSTRAINT_LESS_THAN, CONSTRAINT_EQUALS_TO, CONSTRAINT_GREATER_THAN,
         CONSTRAINT_MAXIMIZE, CONSTRAINT_MINIMIZE]
    )
    @pytest.mark.parametrize(
        'constraint_init_parameter_template',
        [CONSTRAINT_LESS_THAN, CONSTRAINT_EQUALS_TO, CONSTRAINT_GREATER_THAN]
    )
    @pytest.mark.parametrize(
        'score, threshold_score, init_parameter, threshold_init_parameter',
        [(SCORES[0], MIDDLE_SCORE, INIT_PARAMETERS[1], MIDDLE_INIT_PARAMETER)]
    )
    def test_select_by_score_and_init_parameter(
            self, constraint_score_template, constraint_init_parameter_template,
            score, threshold_score,
            init_parameter, threshold_init_parameter):

        experiment = TestExperimentSelect.get_experiment()

        constraint_score = constraint_score_template.format(
            format_score(score), threshold_score)
        constraint_init_parameter = constraint_init_parameter_template.format(
            format_init_parameter(init_parameter), threshold_init_parameter)
        query = combine_constraints(constraint_score, constraint_init_parameter)
        selection = experiment.select(query)

        filter_func_score = TestExperimentSelect.get_filter_for_score(
            constraint_score, score, threshold_score, experiment.models.values()
        )
        satisfying = list(filter(filter_func_score, experiment.models.values()))
        filter_func_init_parameter = TestExperimentSelect.get_filter_for_init_parameter(
            constraint_init_parameter, init_parameter, threshold_init_parameter
        )
        satisfying = list(filter(filter_func_init_parameter, satisfying))

        assert set(selection).issubset(set(satisfying)), \
            f'Some models among selected don\'t satisfy ' \
            f'the query "{query}"'

    @pytest.mark.xfail
    def test_empty_level(self):
        level_with_models = 1
        level_without_models = 2

        experiment = TestExperimentSelect.get_experiment(with_models=False)
        TestExperimentSelect.set_models(
            experiment, [MockTopicModel('model', depth=level_with_models)]
        )

        selection = experiment.select(TestExperimentSelect.query_sample, level=level_without_models)

        assert all(m.depth == level_without_models for m in selection),\
            'Some models have depth other than required'
        assert len(selection) == 0,\
            'Some models selected on level with no models'

    @pytest.mark.xfail
    @pytest.mark.parametrize('num_models', [1, 2])
    @pytest.mark.parametrize('difference_with_num_satisfying', [1, 0, -1])
    @pytest.mark.parametrize('total_num_models', [20])
    @pytest.mark.parametrize(
        'score, target_value, other_value, query_template',
        [
            (SCORES[0], 100, 1, CONSTRAINT_EQUALS_TO.format('{0}', 100)),
            (SCORES[0], 100, 1, CONSTRAINT_MAXIMIZE),
            (SCORES[0], 100, 1000, CONSTRAINT_MINIMIZE),
            (SCORES[0], 100, 1, CONSTRAINT_GREATER_THAN.format('{0}', 1)),
            (SCORES[0], 100, 1000, CONSTRAINT_LESS_THAN.format('{0}', 1000))
        ]
    )
    def test_num_models(
            self, num_models, total_num_models, difference_with_num_satisfying,
            score, target_value, other_value, query_template):

        experiment = TestExperimentSelect.get_experiment(with_models=False)

        # Don't consider "num_satisfying = 0" here
        num_satisfying = max(num_models + difference_with_num_satisfying, 1)
        num_other = max(total_num_models - num_satisfying, 0)

        models_satisfying = [
            MockTopicModel(f'model_satisfying_{i}').set_score(score, [target_value])
            for i in range(num_satisfying)
        ]
        models_other = [
            MockTopicModel(f'model_other_{i}').set_score(score, [other_value])
            for i in range(num_other)
        ]

        TestExperimentSelect.set_models(experiment, models_satisfying + models_other)

        query = query_template.format(format_score(score))
        selection_first_time = experiment.select(query, models_num=num_models)
        selection_second_time = experiment.select(query, models_num=num_models)

        assert len(selection_first_time) == min(num_models, num_satisfying),\
            'Wrong number of selected models on first select'
        assert len(selection_second_time) == min(num_models, num_satisfying),\
            'Wrong number of selected models on second select'
        assert selection_first_time == selection_second_time,\
            'First and second select() results not the same'

    @pytest.mark.xfail
    @pytest.mark.parametrize('with_models', [True, False])
    def test_blank_query(self, with_models):
        experiment = TestExperimentSelect.get_experiment(with_models=False)

        if with_models:
            TestExperimentSelect.set_models(
                experiment, [MockTopicModel('model_name').set_score('some_score', [1])]
            )

        selection = experiment.select('')

        assert len(selection) == 0, 'Some models selected'

    @pytest.mark.xfail
    @pytest.mark.parametrize('score, threshold', [(SCORES[0], MIDDLE_SCORE)])
    def test_whitespace(self, score, threshold):
        experiment = TestExperimentSelect.get_experiment()

        one_space = ' '
        two_spaces = '  '
        tab = '\t'
        newline = '\n'

        query_one_space_template =\
            f'{{0}}{one_space}{GREATER}{one_space}{{1}}'
        query_two_spaces_template =\
            f'{{0}}{two_spaces}{GREATER}{two_spaces}{{1}}'
        query_tab_template =\
            f'{{0}}{tab}{GREATER}{tab}{{1}}'
        query_newline_template =\
            f'{{0}}{newline}{GREATER}{newline}{{1}}'
        query_space_at_the_beginning_template =\
            f'{one_space}{{0}}{one_space}{GREATER}{one_space}{{1}}'
        query_space_at_the_end_template =\
            f'{{0}}{one_space}{GREATER}{one_space}{{1}}{one_space}'

        selections = [
            experiment.select(q)
            for q in [
                query_one_space_template.format(format_score(score), threshold),
                query_two_spaces_template.format(format_score(score), threshold),
                query_tab_template.format(format_score(score), threshold),
                query_newline_template.format(format_score(score), threshold),
                query_space_at_the_beginning_template.format(format_score(score), threshold),
                query_space_at_the_end_template.format(format_score(score), threshold)
            ]
        ]

        assert all(s == selections[0] for s in selections[1:]), 'Some queries differ'

    def test_wrong_case_in_constraints_connector(self):
        experiment = TestExperimentSelect.get_experiment()

        connector_in_wrong_case = AND.lower() if AND != AND.lower() else AND.upper()
        constraint_a = CONSTRAINT_EQUALS_TO.format(
            format_init_parameter(INIT_PARAMETERS[0]), MIDDLE_INIT_PARAMETER
        )
        constraint_b = CONSTRAINT_LESS_THAN.format(
            format_init_parameter(INIT_PARAMETERS[1]), MIDDLE_INIT_PARAMETER
        )
        query = combine_constraints(constraint_a, constraint_b, connector_in_wrong_case)

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.parametrize('max_min', [MAX, MIN])
    def test_wrong_case_in_max_min(self, max_min):
        experiment = TestExperimentSelect.get_experiment()

        max_min_in_wrong_case = max_min.lower()\
            if max_min != max_min.lower()\
            else max_min.upper()
        query = f'{format_score(SCORES[1])} {ARROW_TO} {max_min_in_wrong_case}'

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.parametrize('score', [SCORES[1]])
    def test_wrong_case_in_score(self, score):
        experiment = TestExperimentSelect.get_experiment()

        score_in_wrong_case = score.lower() if score != score.lower() else score.upper()
        query = CONSTRAINT_MAXIMIZE.format(format_score(score_in_wrong_case))

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.parametrize('init_parameter', [INIT_PARAMETERS[1]])
    def test_wrong_case_in_parameter(self, init_parameter):
        experiment = TestExperimentSelect.get_experiment()

        init_parameter_in_wrong_case = init_parameter.lower()\
            if init_parameter != init_parameter.lower()\
            else init_parameter.upper()
        query = CONSTRAINT_EQUALS_TO.format(
            format_init_parameter(init_parameter_in_wrong_case), MIDDLE_INIT_PARAMETER
        )

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        'init_parameter, threshold', [(INIT_PARAMETERS[1], MIDDLE_INIT_PARAMETER)]
    )
    @pytest.mark.parametrize(
        'wrong_prefix', ['model', 'model,', 'mdel.', 'Model.', '']
    )
    def test_wrong_parameter_prefix(self, init_parameter, threshold, wrong_prefix):
        experiment = TestExperimentSelect.get_experiment()

        query = CONSTRAINT_EQUALS_TO.format(wrong_prefix + init_parameter, threshold)

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.parametrize(
        'constraint_a',
        [CONSTRAINT_EQUALS_TO.format(format_score(SCORES[0]), MIDDLE_SCORE)]
    )
    @pytest.mark.parametrize(
        'constraint_b',
        [CONSTRAINT_LESS_THAN.format(
            format_init_parameter(INIT_PARAMETERS[1]), MIDDLE_INIT_PARAMETER)]
    )
    @pytest.mark.parametrize(
        'wrong_connector',
        [AND + AND, AND + ' ' + AND, 'or', 'model', INIT_PARAMETER_PREFIX,
         ARROW_TO, GREATER, LESS, EQUALS, '']
    )
    def test_wrong_constraints_connector(self, constraint_a, constraint_b, wrong_connector):
        experiment = TestExperimentSelect.get_experiment()

        query = combine_constraints(constraint_a, constraint_b, wrong_connector)

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.parametrize(
        'query_template', [f'{format_score(SCORES[0])} {{0}} {MIDDLE_SCORE}']
    )
    @pytest.mark.parametrize(
        'wrong_sign',
        [
            '>=', '<=', '<>', '<<', '>>',  # inequality
            '==', '===', 'equals', 'equal', 'is',  # equality
            '=>', '=<'  # others
        ]
    )
    def test_wrong_comparison_sign(self, query_template, wrong_sign):
        experiment = TestExperimentSelect.get_experiment()

        query = query_template.format(wrong_sign)

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.parametrize(
        'query_template', [f'{format_score(SCORES[0])} {LESS} {{0}}']
    )
    @pytest.mark.parametrize(
        'not_a_number', ['NUMBER', 'number', LESS, GREATER, EQUALS, ARROW_TO, MAX, MIN, AND]
    )
    def test_not_a_number(self, query_template, not_a_number):
        experiment = TestExperimentSelect.get_experiment()

        query = query_template.format(not_a_number)

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.parametrize(
        'query_template', [f'{format_score(SCORES[0])} {{0}} {MIN}']
    )
    @pytest.mark.parametrize(
        'wrong_arrow',
        ['<-', '-<', '>-', '=>', '<=', '-->', 'to', '→', '←', '->>', '-><',
         EQUALS, GREATER, LESS, '']
    )
    def test_wrong_arrow(self, query_template, wrong_arrow):
        experiment = TestExperimentSelect.get_experiment()

        query = query_template.format(wrong_arrow)

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.parametrize(
        'query_template', [f'{format_score(SCORES[1])} {ARROW_TO} {{0}}']
    )
    @pytest.mark.parametrize(
        'wrong_max_min',
        [1, 1.2, 'inf', '+inf', 'maximize',
         MAX + MAX, MAX + MIN, ARROW_TO, GREATER, LESS, EQUALS, '']
    )
    def test_wrong_max_min(self, query_template, wrong_max_min):
        experiment = TestExperimentSelect.get_experiment()

        query = query_template.format(wrong_max_min)

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        'constraint',
        [
            CONSTRAINT_GREATER_THAN.format(format_score(SCORES[1]), MIDDLE_SCORE),
            CONSTRAINT_EQUALS_TO.format(
                format_init_parameter(INIT_PARAMETERS[1]), MIDDLE_INIT_PARAMETER),
            CONSTRAINT_MINIMIZE.format(format_score(SCORES[0]))
        ]
    )
    def test_duplicate_constraint(self, constraint):
        experiment = TestExperimentSelect.get_experiment()

        query_one_constraint = constraint
        query_duplicate_constraints = combine_constraints(constraint, constraint)

        selection_with_one = experiment.select(query_one_constraint)
        selection_with_duplicate = experiment.select(query_duplicate_constraints)

        assert selection_with_one == selection_with_duplicate,\
            'Duplicate constraints changed query result'

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        'constraint_to_duplicate',
        [
            CONSTRAINT_LESS_THAN.format(format_score(SCORES[0]), MIDDLE_SCORE),
            CONSTRAINT_EQUALS_TO.format(
                format_init_parameter(INIT_PARAMETERS[0]), MIDDLE_INIT_PARAMETER),
            CONSTRAINT_MAXIMIZE.format(format_score(SCORES[0]))
        ]
    )
    @pytest.mark.parametrize(
        'constraint_other',
        [
            CONSTRAINT_GREATER_THAN.format(format_score(SCORES[1]), MIDDLE_SCORE),
            CONSTRAINT_EQUALS_TO.format(
                format_init_parameter(INIT_PARAMETERS[1]), MIDDLE_INIT_PARAMETER),
            CONSTRAINT_MINIMIZE.format(format_score(SCORES[1]))
        ]
    )
    def test_duplicate_constraint_after_another(self, constraint_to_duplicate, constraint_other):
        if ARROW_TO in constraint_to_duplicate and ARROW_TO in constraint_other:
            # Several "-> max/min" not allowed
            return

        experiment = TestExperimentSelect.get_experiment()

        query_constraint_and_other = combine_constraints(constraint_to_duplicate, constraint_other)
        query_duplicate_constraints_and_other = combine_constraints(
            constraint_to_duplicate, constraint_other, constraint_to_duplicate)

        selection_with_one = experiment.select(query_constraint_and_other)
        selection_with_duplicate = experiment.select(query_duplicate_constraints_and_other)

        assert selection_with_one == selection_with_duplicate,\
            'Other constraint changed query result'

    @pytest.mark.parametrize(
        'parameter, soft_constraint_template, hard_constraint_template',
        [
            (
                format_score(SCORES[0]),
                CONSTRAINT_GREATER_THAN.format('{0}', MIN_SCORE),
                CONSTRAINT_GREATER_THAN.format('{0}', MIDDLE_SCORE)
            ),
            (
                format_init_parameter(INIT_PARAMETERS[0]),
                CONSTRAINT_GREATER_THAN.format('{0}', MIN_INIT_PARAMETER),
                CONSTRAINT_GREATER_THAN.format('{0}', MIDDLE_INIT_PARAMETER)
            ),
            (
                format_score(SCORES[1]),
                CONSTRAINT_GREATER_THAN.format('{0}', MIDDLE_SCORE),
                CONSTRAINT_MAXIMIZE
            )
        ]
    )
    def test_constraints_on_same_attribute(
            self, parameter, soft_constraint_template, hard_constraint_template):

        experiment = TestExperimentSelect.get_experiment()

        soft_constraint = soft_constraint_template.format(parameter)
        hard_constraint = hard_constraint_template.format(parameter)

        soft_query = soft_constraint
        hard_query = combine_constraints(soft_constraint, hard_constraint)

        soft_selection = experiment.select(soft_query)
        hard_selection = experiment.select(hard_query)

        assert set(hard_selection).issubset(set(soft_selection)),\
            'Hard constraint not subset of soft one'
        assert len(hard_selection) < len(soft_selection),\
            'Hard constraint not proper subset of soft one'

    @pytest.mark.parametrize(
        'score, threshold, constraint_template, optimization_template',
        [
            # constraint affects
            (SCORES[0], MIDDLE_SCORE, CONSTRAINT_LESS_THAN, CONSTRAINT_MAXIMIZE),
            # constraint affects
            (SCORES[1], MIDDLE_SCORE, CONSTRAINT_GREATER_THAN, CONSTRAINT_MINIMIZE),
            # constraint affects
            (SCORES[1], MIDDLE_SCORE, CONSTRAINT_EQUALS_TO, CONSTRAINT_MINIMIZE),
            # constraint doesn't affect
            (SCORES[1], MIDDLE_SCORE, CONSTRAINT_LESS_THAN, CONSTRAINT_MINIMIZE),
            # constraint doesn't affect
            (SCORES[1], MIDDLE_SCORE, CONSTRAINT_GREATER_THAN, CONSTRAINT_MAXIMIZE)
        ]
    )
    def test_constrained_optimization(
            self, score, threshold, constraint_template, optimization_template):

        experiment = TestExperimentSelect.get_experiment()

        constraint = constraint_template.format(format_score(score), threshold)
        optimization = optimization_template.format(format_score(score))
        query = combine_constraints(constraint, optimization)
        selection = experiment.select(query)

        filter_func_constraint = TestExperimentSelect.get_filter_for_score(
            constraint, score, threshold, experiment.models.values()
        )
        satisfying = list(filter(filter_func_constraint, experiment.models.values()))
        filter_func_optimization = TestExperimentSelect.get_filter_for_score(
            optimization, score, None, satisfying
        )
        satisfying = list(filter(filter_func_optimization, satisfying))

        assert set(selection).issubset(set(satisfying)),\
            f'Some selected models don\'t satisfy the query "{query}"'

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        'parameter, threshold',
        [
            (format_score(SCORES[1]), MIDDLE_SCORE),
            (format_init_parameter(INIT_PARAMETERS[1]), MIDDLE_INIT_PARAMETER)
        ]
    )
    @pytest.mark.parametrize('signs', combinations([LESS, GREATER, EQUALS], 2))
    def test_constraints_on_same_attribute_contradict(self, parameter, threshold, signs):
        experiment = TestExperimentSelect.get_experiment()

        constraint_template = f'{{0}} {{1}} {{2}}'
        query = combine_constraints(
            *[constraint_template.format(parameter, sign, threshold)
              for sign in signs]
        )
        selection = experiment.select(query)

        assert len(selection) == 0, 'Some models selected'

    @pytest.mark.parametrize('score', [SCORES[0]])
    def test_error_optimizations_contradict(self, score):
        experiment = TestExperimentSelect.get_experiment()

        optimization_max = CONSTRAINT_MAXIMIZE.format(score)
        optimization_min = CONSTRAINT_MINIMIZE.format(score)
        query = combine_constraints(optimization_max, optimization_min)

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        'parameter, opposite_constraints',
        [
            (
                format_score(SCORES[0]),
                [CONSTRAINT_LESS_THAN.format('{0}', MIDDLE_SCORE),
                 CONSTRAINT_GREATER_THAN.format('{0}', MIDDLE_SCORE)]
            ),
            (
                format_init_parameter(INIT_PARAMETERS[1]),
                [CONSTRAINT_EQUALS_TO.format('{0}', MIDDLE_INIT_PARAMETER),
                 CONSTRAINT_LESS_THAN.format('{0}', MIDDLE_INIT_PARAMETER)]
            )
        ]
    )
    def test_warning_constraints_contradict(self, parameter, opposite_constraints):
        experiment = TestExperimentSelect.get_experiment()

        query = combine_constraints(*[c.format(parameter) for c in opposite_constraints])

        with pytest.warns(UserWarning):
            _ = experiment.select(query)

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        'query_template',
        [
            CONSTRAINT_GREATER_THAN.format('{0}', 0),
            CONSTRAINT_LESS_THAN.format('{0}', 0),
            CONSTRAINT_EQUALS_TO.format('{0}', 0),
            CONSTRAINT_MAXIMIZE.format('{0}'),
            CONSTRAINT_MINIMIZE.format('{0}')
        ]
    )
    @pytest.mark.parametrize(
        'get_models_func',
        [
            # Pass func-s here, not func()-s, because it seems pytest does not like func()-s
            # (test running slows greatly and may even lead to system freeze)
            get_models_with_two_scores_two_init_parameters,
            get_models_with_one_init_parameter
        ]
    )
    def test_unknown_score(self, query_template, get_models_func):
        experiment = TestExperimentSelect.get_experiment(with_models=False)
        TestExperimentSelect.set_models(experiment, get_models_func())

        query = query_template.format(format_score('UNKNOWN_SCORE'))

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        'query_template',
        [
            CONSTRAINT_GREATER_THAN.format('{0}', 0),
            CONSTRAINT_LESS_THAN.format('{0}', 0),
            CONSTRAINT_EQUALS_TO.format('{0}', 0),
        ]
    )
    @pytest.mark.parametrize(
        'get_models_func',
        [
            get_models_with_two_scores_two_init_parameters,
            get_models_with_one_score
        ]
    )
    def test_unknown_init_parameter(self, query_template, get_models_func):
        experiment = TestExperimentSelect.get_experiment(with_models=False)
        TestExperimentSelect.set_models(experiment, get_models_func())

        query = query_template.format(format_init_parameter('UNKNOWN_INIT_PARAMETER'))

        with pytest.raises(ValueError):
            _ = experiment.select(query)

    @pytest.mark.parametrize(
        'constraints',
        [
            (
                # one score, one init parameter
                CONSTRAINT_MINIMIZE.format(
                    format_score(SCORES[0])),
                CONSTRAINT_EQUALS_TO.format(
                    format_init_parameter(INIT_PARAMETERS[1]), MIDDLE_INIT_PARAMETER)
            ),
            (
                # two init parameters
                CONSTRAINT_GREATER_THAN.format(
                    format_init_parameter(INIT_PARAMETERS[0]), MIDDLE_INIT_PARAMETER),
                CONSTRAINT_EQUALS_TO.format(
                    format_init_parameter(INIT_PARAMETERS[1]), MIDDLE_INIT_PARAMETER)
            ),
            (
                # two scores
                CONSTRAINT_GREATER_THAN.format(
                    format_score(SCORES[0]), MIDDLE_SCORE),
                CONSTRAINT_LESS_THAN.format(
                    format_score(SCORES[1]), MIDDLE_SCORE)
            ),
            (
                # two scores, one init parameter
                CONSTRAINT_MINIMIZE.format(
                    format_score(SCORES[0])),
                CONSTRAINT_EQUALS_TO.format(
                    format_init_parameter(INIT_PARAMETERS[1]), MIDDLE_INIT_PARAMETER),
                CONSTRAINT_GREATER_THAN.format(
                    format_score(SCORES[1]), MIDDLE_SCORE)
            ),
            (
                # one score, two init parameters
                CONSTRAINT_GREATER_THAN.format(
                    format_score(SCORES[1]), MIDDLE_SCORE),
                CONSTRAINT_GREATER_THAN.format(
                    format_init_parameter(INIT_PARAMETERS[0]), MIDDLE_INIT_PARAMETER),
                CONSTRAINT_LESS_THAN.format(
                    format_init_parameter(INIT_PARAMETERS[1]), MIDDLE_INIT_PARAMETER)
            )
        ]
    )
    def test_change_order(self, constraints):
        experiment = TestExperimentSelect.get_experiment()

        query_ab = combine_constraints(*constraints)
        query_ba = combine_constraints(*constraints[::-1])

        selection_ab = experiment.select(query_ab)
        selection_ba = experiment.select(query_ba)

        assert selection_ab == selection_ba,\
            'Different select() results if change order of constraints'

    @pytest.mark.parametrize(
        'query',
        [
            CONSTRAINT_LESS_THAN.format(format_score(SCORES[0]), MIDDLE_SCORE),
            CONSTRAINT_EQUALS_TO.format(
                format_init_parameter(INIT_PARAMETERS[0]), MIDDLE_INIT_PARAMETER),
            CONSTRAINT_MAXIMIZE.format(format_score(SCORES[1]))
        ]
    )
    def test_select_several_times(self, query):
        experiment = TestExperimentSelect.get_experiment()

        selection_a = experiment.select(query)
        selection_b = experiment.select(query)
        selection_c = experiment.select(query)

        assert selection_a == selection_b, 'Different select results after on second call'
        assert selection_b == selection_c, 'Different select results after on third call'

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        'query_template', [CONSTRAINT_LESS_THAN]
    )
    @pytest.mark.parametrize(
        'init_parameter, threshold_satisfying_all', [(INIT_PARAMETERS[0], MAX_INIT_PARAMETER + 1)]
    )
    @pytest.mark.parametrize(
        'num_models', [0, 1, 2, 5, 'minus-one', 'equals', 'plus-one', 'very-big']
    )
    def test_num_and_models(
            self, query_template, init_parameter, threshold_satisfying_all, num_models):

        experiment = TestExperimentSelect.get_experiment()

        total_num_models = len(experiment.models)

        if isinstance(num_models, int):
            pass
        elif num_models == 'minus-one':
            num_models = total_num_models - 1
        elif num_models == 'equals':
            num_models = total_num_models
        elif num_models == 'plus-one':
            num_models = total_num_models + 1
        elif num_models == 'very-big':
            num_models = 100 * total_num_models
        else:
            raise ValueError()

        query_satisfying_all = query_template.format(
            format_init_parameter(init_parameter), threshold_satisfying_all)
        selection = experiment.select(query_satisfying_all, num_models)

        filter_func = TestExperimentSelect.get_filter_for_init_parameter(
            query_satisfying_all, init_parameter, threshold_satisfying_all
        )
        satisfying = list(filter(filter_func, experiment.models.values()))

        if len(satisfying) > total_num_models:
            raise RuntimeError('Satisfying models more than all models')

        assert len(selection) <= total_num_models, 'Select more models than available'

        if len(selection) > num_models:
            assert False,\
                f'Return more models than required: "{len(selection)}" > "{num_models}". ' \
                f'Total number of models satisfying the query: "{len(satisfying)}"'
        elif len(selection) < num_models:
            assert set(selection) == set(satisfying),\
                'Return fewer models, but they are not the ones that satisfy the condition'
        else:
            assert set(selection).issubset(set(satisfying)),\
                'Return models number as requested, ' \
                'but not all returned models satisfy the constraint'

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        'query_satisfying_all',
        [CONSTRAINT_LESS_THAN.format(
            format_init_parameter(INIT_PARAMETERS[0]), MAX_INIT_PARAMETER + 1)]
    )
    def test_warning_fewer_than_requested(self, query_satisfying_all):
        experiment = TestExperimentSelect.get_experiment()

        total_num_models = len(experiment.models)
        num_models = 100 * total_num_models

        with pytest.warns(UserWarning):
            _ = experiment.select(query_satisfying_all, num_models)