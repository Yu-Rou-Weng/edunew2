from django.core.exceptions import ValidationError
from django.db import models
from django.forms.models import model_to_dict


class choice_mixin(models.TextChoices):
    @classmethod
    def to_dict(cls):
        return [{'value': str(key), 'text': cls(key).label} for key in cls]


# https://docs.djangoproject.com/en/3.1/ref/models/fields/#enumeration-types
class SimStatus(choice_mixin):
    ON = 'on', 'on'
    OFF = 'off', 'off'


class Distribution(choice_mixin):
    NORMAL = 'NO', 'Normal'
    GAMMA = 'GA', 'Gamma'
    UNIFORM = 'UN', 'Uniform'


class VariableType(choice_mixin):
    INT = 'int', 'int'
    FLOAT = 'float', 'float'


# Django Model will automatically create id field,
# We don't need to assign
class User(models.Model):
    u_id = models.IntegerField(primary_key=True)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=255, blank=True)
    sub = models.CharField(max_length=255, blank=True)
    email = models.CharField(max_length=254, blank=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(blank=True, null=True)
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)


class RefreshToken(models.Model):
    token = models.TextField()
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='refresh_tokens'
    )


class AccessToken(models.Model):
    token = models.TextField()
    expires_at = models.DateTimeField()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='access_tokens'
    )
    refresh_token = models.ForeignKey(
        RefreshToken,
        on_delete=models.CASCADE,
        related_name='access_tokens'
    )


class Project(models.Model):
    p_id = models.IntegerField(primary_key=True)
    p_name = models.CharField(max_length=255)
    sim = models.CharField(
        max_length=3,
        choices=SimStatus.choices,
        default=SimStatus.OFF
    )
    u_id = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects'
    )

    def __str__(self):
        return 'p_id: {}\tp_name: {}\tsim: {}'.format(
            self.p_id,
            self.p_name,
            self.sim
        )

    def to_dict(self, fetch_dfo=False):
        project = model_to_dict(self)
        project['do_list'] = [
            do.to_dict() if fetch_dfo else model_to_dict(do)
            for do in self.device_objects.all()
        ]
        return project


class DeviceObject(models.Model):
    do_id = models.IntegerField(primary_key=True)
    dm_name = models.CharField(max_length=255)
    sim = models.CharField(
        max_length=3,
        choices=SimStatus.choices,
        default=SimStatus.OFF
    )
    p_id = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='device_objects'
    )
    ccm_d_id = models.IntegerField(default=None, blank=True, null=True)
    ag_token = models.CharField(
        max_length=36,
        default='',
        blank=True,
    )
    is_default = models.BooleanField(default=True)

    def __str__(self):
        return 'dm_name: {}\tdo_id: {}\tp_id: {}\tsim: {}'.format(
            self.dm_name,
            self.do_id,
            self.p_id_id,
            self.sim
        )

    def to_dict(self):
        do = model_to_dict(self)
        do['dfo_list'] = [dfo.to_dict() for dfo in self.device_feature_objects.all()]

        return do


class DeviceFeatureObject(models.Model):
    dfo_id = models.IntegerField(primary_key=True)
    df_name = models.CharField(max_length=255)
    do_id = models.ForeignKey(
        DeviceObject,
        on_delete=models.CASCADE,
        related_name='device_feature_objects'
    )
    is_default = models.BooleanField(default=True)

    def __str__(self):
        return 'df_name: {}\tdfo_id: {}\t'.format(
            self.df_name,
            self.dfo_id
        )

    def to_dict(self):
        dfo = model_to_dict(self, ['dfo_id', 'df_name'])
        dfo['time_distribution'] = model_to_dict(self.time_distribution)
        dfo['value_distributions'] = [
            model_to_dict(vd) for vd in self.value_distributions.all()
        ]

        return dfo


class DistributionModel(models.Model):
    distribution = models.CharField(
        max_length=2,
        choices=Distribution.choices,
        default=Distribution.NORMAL
    )
    mean = models.FloatField(default=0.5)
    var = models.FloatField(default=0.25)
    seed = models.IntegerField()
    min = models.FloatField(default=0)
    max = models.FloatField(default=1)

    class Meta:
        abstract = True

    def clean(self):
        errors = {}

        if self.min > self.max:
            errors.update({'min': 'min > max'})

        if self.distribution == Distribution.GAMMA:
            if self.mean <= 0:
                errors.update({'mean': 'mean should be positive.'})
            if self.var <= 0:
                errors.update({'variance': 'variance should be positive.'})

        if(errors):
            raise ValidationError(errors)

        return


class ValueDistribution(DistributionModel):
    dfo_id = models.ForeignKey(
        DeviceFeatureObject,
        on_delete=models.CASCADE,
        related_name='value_distributions'
    )
    param_i = models.IntegerField()
    param_type = models.CharField(
        max_length=5,
        choices=VariableType.choices,
        default=VariableType.FLOAT
    )

    # include Distribution class

    class Meta:
        unique_together = ('dfo_id', 'param_i')

    def __str__(self):
        return 'Value: dfo_id: {}\tparam_i: {}\tdistribution: {}'.format(
            self.dfo_id,
            self.param_i,
            self.distribution
        )


class TimeDistribution(DistributionModel):
    dfo_id = models.OneToOneField(
        DeviceFeatureObject,
        on_delete=models.CASCADE,
        related_name='time_distribution',
    )

    # include Distribution class

    def __str__(self):
        return 'Time: dfo_id: {}\tdistribution: {}'.format(
            self.dfo_id,
            self.distribution
        )
