.PHONY: demo test ui clean

demo:
python run.py --bundle tests/bundles/scenario_01

test:
python run.py --bundle tests/bundles/scenario_01
python run.py --bundle tests/bundles/scenario_02
python run.py --bundle tests/bundles/scenario_03
python run.py --bundle tests/bundles/scenario_04
python run.py --bundle tests/bundles/scenario_05
python run.py --bundle tests/bundles/scenario_06
python run.py --bundle tests/bundles/scenario_07
python run.py --bundle tests/bundles/scenario_08
python run.py --bundle tests/bundles/scenario_09

ui:
python -m streamlit run app/ui/streamlit_app.py

clean:
rmdir /s /q runs 2>nul || true
