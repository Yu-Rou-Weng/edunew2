"""Django View for Autogen Subsystem."""
from django.db import models


class Device(models.Model):
    """
    The AutoGen Device record.

    :param code: The ida code for AutoGen Device executed.
    :param token: The token of AutoGen Device, used to create/search/delete.
    """
    code = models.TextField(blank=False)
    token = models.CharField(max_length=36, unique=True)
    version = models.IntegerField(default=2)
    exception = models.TextField(blank=False, default='')
    created = models.DateTimeField(auto_now_add=True)
    started = models.DateTimeField(null=True)
    stoped = models.DateTimeField(null=True)
    deleted = models.DateTimeField(null=True)

    def to_dict(self):
        return {k: getattr(self, k) for k in ['code', 'token', 'version']}
