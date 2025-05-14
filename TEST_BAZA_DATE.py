from DATABASE import db

# De apelat la start

import time
from datetime import datetime

now_epoch = time.time()
now_human = datetime.now()
now_from_epoch = datetime.fromtimestamp(now_epoch)

print("Timp din time.time():", now_epoch)
print("Timp sistem (datetime.now()):", now_human)
print("Timp convertit din time.time():", now_from_epoch)




print("Tag:", db.GET_VAR("tag"))
print("Ultima actualizare:", db.GET_VAR("lastTimeUpdated"))
print("Tag disponibil?", db.GET_FLAG("isTagAvailable"))
print("Danger level:", db.GET_FLAG("isDanger"))


