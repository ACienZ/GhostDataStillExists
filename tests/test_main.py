from templete_project.main import main


def test_main_prints_hello_world(capsys):
    main()
    captured = capsys.readouterr()
    assert captured.out == "Hello, World!\n"
