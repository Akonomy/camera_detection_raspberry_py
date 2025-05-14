from DATABASE import db
import json

db.INIT()

# Group: box
db.REGISTER("box_id", groups=["box"])
db.REGISTER("zone", groups=["box"])
db.REGISTER("color", groups=["box"])
db.REGISTER("letters", groups=["box"])

# Group: task
db.REGISTER("task_id", groups=["task"])
db.REGISTER("from_zone", groups=["task"])
db.REGISTER("to_zone", groups=["task"])
db.REGISTER("box_id", groups=["task"])
db.REGISTER("path_id", groups=["task"])
db.REGISTER("path_name", groups=["task"])
db.REGISTER("status", groups=["task"])
db.REGISTER("progress", groups=["task"])

# Group: path
db.REGISTER("path_id", groups=["path"])
db.REGISTER("path_human", groups=["path"])
db.REGISTER("path_stm32", groups=["path"])
db.REGISTER("zone_path", groups=["path"])
db.REGISTER("zone_num", groups=["path"])
db.REGISTER("tags_possible", groups=["path"])
db.REGISTER("active", groups=["path"])

# Group: utils
db.REGISTER("tag", groups=["utils"])
db.REGISTER("sensor", groups=["utils"])

# Group: flags
db.REGISTER("task_status", groups=["flags"])
db.REGISTER("calibrated", groups=["flags"])
db.REGISTER("tag_ready", groups=["flags"])
db.REGISTER("danger", groups=["flags"])
db.REGISTER("parked", groups=["flags"])

print("All variables registered.")