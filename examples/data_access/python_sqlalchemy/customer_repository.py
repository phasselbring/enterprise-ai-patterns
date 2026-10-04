# SQLAlchemy 2.x query shape:
#
# stmt = select(Customer).where(Customer.state == state).order_by(Customer.name)
# with Session(engine) as session:
#     return list(session.scalars(stmt).all())
