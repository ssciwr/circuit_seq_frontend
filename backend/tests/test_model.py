import circuit_seq_server.model as model
import datetime


def _count_settings() -> int:
    return len(
        model.db.session.execute(model.db.select(model.Settings)).scalars().all()
    )


def test_settings(app, tmp_path):
    with app.app_context():
        assert _count_settings() == 1
        settings = model.get_current_settings()
        assert _count_settings() == 1
        assert settings["plate_n_rows"] == 8
        assert settings["plate_n_cols"] == 12
        settings["plate_n_rows"] = 14
        settings["plate_n_cols"] = 18
        email = "test@test.com"
        msg, code = model.set_current_settings(email, settings)
        assert code == 200
        assert "Settings updated" in msg
        assert _count_settings() == 2
        new_settings = model.get_current_settings()
        assert new_settings["plate_n_rows"] == 14
        assert new_settings["plate_n_cols"] == 18
        # settings dict missing required fields is a no-op
        msg, code = model.set_current_settings(email, {"plate_n_rows": 10})
        assert code == 401
        assert "settings not updated" in msg
        assert _count_settings() == 2
        assert new_settings["plate_n_rows"] == 14
        assert new_settings["plate_n_cols"] == 18
        msg, code = model.set_current_settings(
            email,
            {"plate_n_rows": 10, "plate_n_cols": 2, "running_options": ["x", "y"]},
        )
        assert code == 200
        assert "Settings updated" in msg
        assert _count_settings() == 3
        new_settings = model.get_current_settings()
        assert new_settings["plate_n_rows"] == 10
        assert new_settings["plate_n_cols"] == 2
        assert new_settings["running_options"] == ["x", "y"]


def test_add_new_sample(app, tmp_path):
    with app.app_context():
        year, week, day = datetime.date.today().isocalendar()
        current_date = datetime.date.fromisocalendar(year, week, day)
        this_week_samples = model.db.select(model.Sample).filter(
            model.Sample.date >= current_date
        )
        assert len(model.db.session.execute(this_week_samples).scalars().all()) == 0
        assert model.count_samples_this_week() == 0
        # add a sample without a reference sequence
        new_sample = model.add_new_sample(
            "u1@embl.de", "s1", "running option", None, str(tmp_path)
        )
        assert new_sample is not None
        assert new_sample.email == "u1@embl.de"
        assert new_sample.name == "s1"
        assert new_sample.running_option == "running option"
        assert new_sample.primary_key == f"{year%100}_{week}_A1"
        assert new_sample.date == current_date
        assert new_sample.reference_sequence_description is None
        samples = model.db.session.execute(this_week_samples).scalars().all()
        assert len(samples) == 1
        assert samples[0] == new_sample
        assert model.count_samples_this_week() == 1


def _count_users() -> int:
    return len(model.db.session.execute(model.db.select(model.User)).scalars().all())


def test_add_new_user_invalid(app):
    password_valid = "abcABC123"
    email_valid = "joe.bloggs@embl.de"
    with app.app_context():
        for email in ["joe@gmail.com", "@embl.de"]:
            msg, code = model.add_new_user(email, password_valid, is_admin=False)
            assert code == 401
            assert "email" in msg
        for password in [
            "",
            "abc123A",
            "passwordpassword",
            "abc12345678",
            "asd!(*&@#@!(*#%ASDASDFGK",
        ]:
            msg, code = model.add_new_user(email_valid, password, is_admin=False)
            assert code == 401
            assert "Password" in msg


def test_add_new_user_valid(app):
    email = "x@embl.de"
    password = "passwdP1"
    with app.app_context():
        n_users = _count_users()
        msg, code = model.add_new_user(email, password, is_admin=False)
        assert code == 200
        assert _count_users() == n_users + 1
        user = model.db.session.execute(
            model.db.select(model.User).filter(model.User.email == email)
        ).scalar_one_or_none()
        assert user is not None
        assert user.email == email
        assert user.is_admin is False
        # check password
        assert user.check_password("wrong") is False
        assert user.check_password(password) is True
        # set new password
        assert user.set_password("wrong", "new") is False
        assert user.check_password(password) is True
        assert user.set_password(password, "newPassword2") is True
        # check new password
        assert user.check_password(password) is False
        assert user.check_password("newPassword2") is True
