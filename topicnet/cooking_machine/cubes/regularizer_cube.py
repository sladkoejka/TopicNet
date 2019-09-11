from .base_cube import BaseCube
from ..routine import transform_complex_entity_to_dict

from copy import deepcopy


class RegularizersModifierCube(BaseCube):
    """
    Allows to create cubes of training and apply them to a topic model.

    """
    def __init__(self, num_iter, regularizer_parameters, reg_search='grid',
                 strategy=None, tracked_score_function=None, verbose=False):
        """
        Initialize stage. Checks params and update internal attributes.

        Parameters
        ----------
        num_iter : str or int
            number of iterations or method
        regularizer_parameters : list[dict] or dict
            regularizers params
        reg_search : str
            "grid", "pair", "add" or "mul". 
            "pair" for elementwise grid search in the case of several regularizers 
            "grid" for the fullgrid search in the case of several regularizers 
            "add" and "mul" for the ariphmetic and geometric progression
            respectively for PerplexityStrategy 
            (Defatult value = "grid")
        strategy : BaseStrategy
            optimization approach (Defatult value = None)
        tracked_score_function : retrieve_score_for_strategy
            optimizable function for strategy (Defatult value = None)
        verbose : bool
            visualization flag (Defatult value = False)

        """  # noqa: W291
        super().__init__(num_iter=num_iter, action='reg_modifier',
                         reg_search=reg_search, strategy=strategy,
                         tracked_score_function=tracked_score_function, verbose=verbose)

        if isinstance(regularizer_parameters, dict):
            regularizer_parameters = [regularizer_parameters]
        self._add_regularizers(regularizer_parameters)

    def _check_all_regularizer_parameters(self, regularizer_parameters):
        """
        Checks and updates params of all regularizers. Inplace.

        Parameters
        ----------
        regularizer_parameters : list of dict

        """
        if len(regularizer_parameters) <= 0:
            raise ValueError("There is no parameters.")

        for i, one_regularizer_parameters in enumerate(regularizer_parameters):
            if not isinstance(one_regularizer_parameters, dict):
                wrong_type = type(one_regularizer_parameters)
                raise ValueError(f"One regularizer should be dict, not {wrong_type}")

        if self.reg_search == "pair":
            # TODO: infinite length support
            grid_size = len(regularizer_parameters[0]["tau_grid"])
            for one_regularizer_parameters in regularizer_parameters:
                if len(one_regularizer_parameters["tau_grid"]) != grid_size:
                    raise ValueError("Grid size is not the same.")

    def _add_regularizers(self, all_regularizer_parameters):
        """

        Parameters
        ----------
        all_regularizer_parameters : list of dict

        """
        self._check_all_regularizer_parameters(all_regularizer_parameters)
        self.raw_parameters = all_regularizer_parameters

        def _retrieve_object(params):
            """

            Parameters
            ----------
            params : dict

            Returns
            -------

            """
            if "regularizer" in params:
                return params["regularizer"]
            else:
                return {"name": params["name"]}

        self.parameters = [
            {
                "object": _retrieve_object(params),
                "field": "tau",
                "values": params['tau_grid']
            }
            for params in all_regularizer_parameters
        ]

    def apply(self, topic_model, one_model_parameter, dictionary=None):
        """
        Applies regularizers and parameters to model.

        Parameters
        ----------
        topic_model : TopicModel
        one_model_parameter : list or tuple
        dictionary : Dictionary
             (Default value = None)

        Returns
        -------
        TopicModel

        """
        new_model = topic_model.clone()
        new_model.parent_model_id = topic_model.model_id
        for regularizer_data in one_model_parameter:
            regularizer, field_name, params = regularizer_data
            if isinstance(regularizer, dict):
                if regularizer['name'] in new_model.regularizers.data:
                    setattr(new_model.regularizers[regularizer['name']],
                            field_name,
                            params)
                else:
                    print(regularizer)
                    error_msg = (f"Regularizer {regularizer['name']} does not exist. "
                                 f"Cannot be modified.")
                    raise ValueError(error_msg)
            elif 'Regularizer' in str(type(regularizer)):
                new_regularizer = deepcopy(regularizer)
                # TODO: '._tau' -> setattr(field_name)
                new_regularizer._tau = params
                new_model.regularizers.add(new_regularizer, overwrite=True)
            else:
                error_msg = f"Regularizer instance or name must be specified for {regularizer}."
                raise ValueError(error_msg)
        return new_model

    def get_jsonable_from_parameters(self):
        """ """
        jsonable_parameters = []
        for one_model_parameters in self.raw_parameters:
            one_jsonable = {"tau_grid": one_model_parameters["tau_grid"]}
            if "regularizer" in one_model_parameters:
                one_regularizer = one_model_parameters['regularizer']
                if not isinstance(one_regularizer, dict):
                    one_regularizer = transform_complex_entity_to_dict(one_regularizer)
                one_jsonable["regularizer"] = one_regularizer
            else:
                one_jsonable["name"] = one_model_parameters["name"]
            jsonable_parameters.append(one_jsonable)

        return jsonable_parameters