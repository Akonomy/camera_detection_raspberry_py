from DATABASE import db

tag = db.GET("tag")
calib = db.GET("calibrated")
ready = db.GET("tag_ready")
danger = db.GET("danger")  # just in case

print("Tag citit:", tag)
print("Calibrated:", calib)
print("Tag ready:", ready)
print("Danger:", danger)
