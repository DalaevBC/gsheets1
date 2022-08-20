import peewee

db = peewee.PostgresqlDatabase(
    database='test1',
    user='postgres',
    password='hamniggun9',
    host='localhost'
)


class BaseModel(peewee.Model):
    class Meta:
        database = db


class GoogleSheeds(BaseModel):
    # В классе описываем таблицу в базе данных
    order_name = peewee.IntegerField()
    price_dollar = peewee.IntegerField()
    date = peewee.DateField()
    price_rubles = peewee.FloatField()
