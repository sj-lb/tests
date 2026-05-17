from time import sleep
from sj.utils.pyspark import get_session, clear_ns

def select_all(fdb, ns: str):
    print(f"\033[mSHOW TABLES IN {ns};\033[36m")
    tbls = fdb.sql(f"SHOW TABLES IN {ns}")
    tbls.show()
    for t in tbls.collect():
        print(f"\033[mSELECT * FROM {ns}.{t[1]};\033[36m")
        fdb.sql(f"SELECT * FROM {ns}.{t[1]}").show()

if __name__ == '__main__':
    fdb = get_session()
    clear_ns(fdb, 'demo_write')

    print("\n\033[mCREATE NAMESPACE demo_write;\033[36m")
    fdb.sql("CREATE NAMESPACE demo_write")
    sleep(2)

    print("\n\033[mCREATE TABLE demo_write.t_sprk(s STRING);\033[36m")
    fdb.sql("CREATE TABLE demo_write.t_sprk(s STRING)")
    sleep(2)

    print("\n\033[mINSERT INTO demo_write.t_sprk VALUES ('is this thing on?');\n\033[36m")
    fdb.sql("INSERT INTO demo_write.t_sprk VALUES ('is this thing on?')")
    sleep(2)

    user_input = ""
    while user_input.lower() != 'q':
        select_all(fdb, 'demo_write')
        user_input = input("\033[m")