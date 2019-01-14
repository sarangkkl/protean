"""Tests for Repository Functionality"""

import pytest

from protean.core.entity import Entity
from protean.core.repository import repo_factory
from protean.core.exceptions import ValidationError, ObjectNotFoundError
from protean.core import field
from protean.impl.repository.dict_repo import DictModel, _databases


class Dog(Entity):
    """This is a dummy Dog Entity class"""
    id = field.Integer(identifier=True)
    name = field.String(required=True, unique=True, max_length=50)
    age = field.Integer(default=5)
    owner = field.String(required=True, max_length=15)


class DogModel(DictModel):
    """ Model for the Dog Entity"""

    class Meta:
        """ Meta class for schema options"""
        entity = Dog
        model_name = 'dogs'


repo_factory.register(DogModel)


class TestRepository:
    """This class holds tests for Repository class"""

    @classmethod
    def teardown_class(cls):
        repo_factory.DogModel.delete_all()

    def test_init(self):
        """Test successful access to the Dog repository"""

        repo_factory.DogModel.filter()
        current_db = dict(repo_factory.DogModel.conn)
        assert current_db['data'] == {'dogs': {}}

    def test_create(self):
        """ Add an entity to the repository"""
        with pytest.raises(ValidationError):
            repo_factory.DogModel.create(name='Johnny', owner='John')

        dog = repo_factory.DogModel.create(id=1, name='Johnny', owner='John')
        assert dog is not None
        assert dog.id == 1
        assert dog.name == 'Johnny'
        assert dog.age == 5
        assert dog.owner == 'John'

        dog = repo_factory.DogModel.get(1)
        assert dog is not None

    def test_update(self):
        """ Update an existing entity in the repository"""

        # Using an invalid id should fail
        with pytest.raises(ObjectNotFoundError):
            repo_factory.DogModel.update(identifier=2, data=dict(age=10))

        # Updates should run the validations
        with pytest.raises(ValidationError):
            repo_factory.DogModel.update(identifier=1, data=dict(age='x'))

        repo_factory.DogModel.update(identifier=1, data=dict(age=10))
        u_dog = repo_factory.DogModel.get(1)
        assert u_dog is not None
        assert u_dog.age == 10

    def test_unique(self):
        """ Test the unique constraints for the entity """

        with pytest.raises(ValidationError) as err:
            repo_factory.DogModel.create(
                id=2, name='Johnny', owner='Carey')
        assert err.value.normalized_messages == {
            'name': ['`dogs` with this `name` already exists.']}

    def test_filter(self):
        """ Query the repository using filters """
        # Add multiple entries to the DB
        repo_factory.DogModel.create(id=2, name='Murdock', age=7, owner='John')
        repo_factory.DogModel.create(id=3, name='Jean', age=3, owner='John')
        repo_factory.DogModel.create(id=4, name='Bart', age=6, owner='Carrie')

        # Filter by the Owner
        dogs = repo_factory.DogModel.filter(owner='John')
        assert dogs is not None
        assert dogs.total == 3
        assert len(dogs.items) == 3

        # Order the results by age
        dogs = repo_factory.DogModel.filter(owner='John', order_by=['-age'])
        assert dogs is not None
        assert dogs.first.age == 10
        assert dogs.first.name == 'Johnny'

    def test_pagination(self):
        """ Test the pagination of the filter results"""
        dogs = repo_factory.DogModel.filter(per_page=2, order_by=['id'])
        assert dogs is not None
        assert dogs.total == 4
        assert len(dogs.items) == 2
        assert dogs.first.id == 1
        assert dogs.has_next
        assert not dogs.has_prev

        dogs = repo_factory.DogModel.filter(page=2, per_page=2, order_by=['id'])
        assert len(dogs.items) == 2
        assert dogs.first.id == 3
        assert not dogs.has_next
        assert dogs.has_prev

    def test_delete(self):
        """ Delete an object in the reposoitory by ID"""
        del_count = repo_factory.DogModel.delete(1)
        assert del_count == 1

        del_count = repo_factory.DogModel.delete(1)
        assert del_count == 0

        with pytest.raises(ObjectNotFoundError):
            repo_factory.DogModel.get(1)

    def test_close_connections(self):
        """ Test closing all connections to the repository"""
        assert 'default' in _databases
        repo_factory.close_connections()
