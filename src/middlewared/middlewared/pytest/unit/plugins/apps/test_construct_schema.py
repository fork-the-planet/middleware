import pytest

from middlewared.plugins.apps.schema_utils import construct_schema
from middlewared.schema import Dict, ValidationErrors


@pytest.mark.parametrize('data, new_values, update', [
    (
        {
            'schema': {
                'groups': [
                    {
                        'name': 'Actual Budget Configuration',
                        'description': 'Configure Actual Budget'
                    },
                ],
                'questions': [
                    {
                        'variable': 'actual_budget',
                        'label': '',
                        'group': 'Actual Budget Configuration',
                        'schema': {
                            'type': 'dict',
                            'attrs': [
                                {
                                    'variable': 'additional_envs',
                                    'label': 'Additional Environment Variables',
                                    'description': 'Configure additional environment variables for Actual Budget.',
                                    'schema': {
                                        'type': 'list',
                                        'default': [],
                                        'items': [
                                            {
                                                'variable': 'env',
                                                'label': 'Environment Variable',
                                                'schema': {
                                                    'type': 'dict',
                                                    'attrs': [
                                                        {
                                                            'variable': 'name',
                                                            'label': 'Name',
                                                            'schema': {
                                                                'type': 'string',
                                                                'required': True
                                                            }
                                                        },
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    },
                ]
            }
        },
        {
            'actual_budget': {'additional_envs': []}
        },
        False,
    ),
])
def test_construct_schema_update_False(data, new_values, update):
    result = construct_schema(data, new_values, update)
    assert isinstance(result['verrors'], ValidationErrors)
    assert len(result['verrors'].errors) == 0
    assert isinstance(result['dict_obj'], Dict)
    assert result['new_values'] == new_values
    assert result['schema_name'] == 'app_create'


@pytest.mark.parametrize('data, new_values, update', [
    (
        {
            'schema': {
                'groups': [
                    {
                        'name': 'Actual Budget Configuration',
                        'description': 'Configure Actual Budget'
                    },
                ],
                'questions': [
                    {
                        'variable': 'actual_budget',
                        'label': '',
                        'group': 'Actual Budget Configuration',
                        'schema': {
                            'type': 'dict',
                            'attrs': [
                                {
                                    'variable': 'additional_envs',
                                    'label': 'Additional Environment Variables',
                                    'description': 'Configure additional environment variables for Actual Budget.',
                                    'schema': {
                                        'type': 'list',
                                        'default': [],
                                        'items': [
                                            {
                                                'variable': 'env',
                                                'label': 'Environment Variable',
                                                'schema': {
                                                    'type': 'dict',
                                                    'attrs': [
                                                        {
                                                            'variable': 'name',
                                                            'label': 'Name',
                                                            'schema': {
                                                                'type': 'string',
                                                                'required': True
                                                            }
                                                        },
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    },
                ]
            }
        },
        {
            'actual_budget': {'additional_envs': []}
        },
        True
    )
])
def test_construct_schema_update_True(data, new_values, update):
    result = construct_schema(data, new_values, update)
    assert isinstance(result['verrors'], ValidationErrors)
    assert len(result['verrors'].errors) == 0
    assert isinstance(result['dict_obj'], Dict)
    assert result['new_values'] == new_values
    assert result['schema_name'] == 'app_update'


@pytest.mark.parametrize('data, update', [
    (
        {
            'schema': {
                'groups': [
                    {
                        'name': 'Actual Budget Configuration',
                        'description': 'Configure Actual Budget'
                    },
                ],
            }
        },
        True,
    ),
])
def test_construct_schema_KeyError(data, update):
    with pytest.raises(KeyError):
        construct_schema(data, {}, update)


@pytest.mark.parametrize('data, new_values, update', [
    (
        {
            'schema': {
                'groups': [
                    {
                        'name': 'Actual Budget Configuration',
                        'description': 'Configure Actual Budget'
                    },
                ],
                'questions': [
                    {
                        'variable': 'actual_budget',
                        'label': '',
                        'group': 'Actual Budget Configuration',
                        'schema': {
                            'type': 'dict',
                            'attrs': [
                                {
                                    'variable': 'additional_envs',
                                    'label': 'Additional Environment Variables',
                                    'description': 'Configure additional environment variables for Actual Budget.',
                                    'schema': {
                                        'type': 'list',
                                        'default': [],
                                        'items': [
                                            {
                                                'variable': 'env',
                                                'label': 'Environment Variable',
                                                'schema': {
                                                    'type': 'dict',
                                                    'attrs': [
                                                        {
                                                            'variable': 'name',
                                                            'label': 'Name',
                                                            'schema': {
                                                                'type': 'string',
                                                                'required': True
                                                            }
                                                        },
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    },
                ]
            }
        },
        {
            'actual_budget': {'additional_envs': 'abc'}
        },
        True,
    ),
])
def test_construct_schema_ValidationError(data, new_values, update):
    result = construct_schema(data, new_values, update)
    assert isinstance(result['verrors'], ValidationErrors)
    assert len(result['verrors'].errors) > 0
    assert isinstance(result['dict_obj'], Dict)
    assert result['new_values'] == new_values
    assert result['schema_name'] == 'app_update' if update else 'app_create'
