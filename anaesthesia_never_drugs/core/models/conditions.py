from django.db import models


# Implementation of Orphanet clinical entities database


class Condition(models.Model):
    name = models.CharField(max_length=255)
    orpha_code = models.CharField(max_length=15)
    date_updated = models.DateTimeField()
    status = models.BooleanField()
    orpha_category = models.ManyToManyField('OrphaCategory', through='ConditionOrphaCategory')


class ConditionSynonym(models.Model):
    name = models.CharField(max_length=255)
    condition = models.ForeignKey(Condition, on_delete=models.CASCADE, related_name='synonyms')


class ConditionOrphaCategory(models.Model):
    condition = models.ForeignKey(Condition, on_delete=models.CASCADE)
    orpha_category = models.ForeignKey('OrphaCategory', on_delete=models.CASCADE)


class OrphaCategory(models.Model):
    name = models.CharField(max_length=255)


