import uuid

import streamlit as st

from app.models.domain import FoodItem
from app.models.nutrition import Meal, MealEntry, MealType
from app.services.nutrition import NutritionService


def render():
    user_id = st.session_state.current_user_id
    selected_date = st.session_state.selected_date

    st.markdown(
        """
        <div style='margin-bottom: 24px;'>
            <h1 class='gradient-text' style='font-size: 2.2rem; margin-bottom: 4px;'>Nutrition & Meals</h1>
            <p style='color: #94a3b8; font-size: 0.95rem; margin: 0;'>Log meals, track macro distributions, and manage your food database catalog.</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if not user_id:
        st.info("💡 Please select or create an active profile in Settings to load nutrition logs.")
        return

    nutrition_service = NutritionService()

    tab_today, tab_food_db = st.tabs(["🍽️ Daily Meal Logs", "🗄️ Food Database"])

    # --- TAB 1: Daily Meal Logs ---
    with tab_today:
        meals = nutrition_service.get_meals_for_date(user_id, selected_date)

        # Calculate daily summaries
        daily_cals = 0.0
        daily_protein = 0.0
        daily_carbs = 0.0
        daily_fat = 0.0

        for m in meals:
            try:
                macros = nutrition_service.calculate_meal_macros(m.meal_id)
                daily_cals += macros.calories
                daily_protein += macros.protein_g
                daily_carbs += macros.carbs_g
                daily_fat += macros.fat_g
            except Exception:
                pass

        # Daily Progress Summary Card
        st.markdown(
            f"""
            <div class='glass-card bento-header'>
                <h4 style='margin:0; color:#5E6AD2;'>Daily Nutrition Scorecard</h4>
                <div style='display: flex; gap: 40px; margin-top: 15px;'>
                    <div>
                        <div class='kpi-lbl'>Total Calories</div>
                        <div class='kpi-val' style='font-size:1.8rem;'>{daily_cals:.0f} kcal</div>
                    </div>
                    <div>
                        <div class='kpi-lbl'>Protein</div>
                        <div class='kpi-val' style='font-size:1.8rem; color:#818CF8;'>{daily_protein:.1f}g</div>
                    </div>
                    <div>
                        <div class='kpi-lbl'>Carbs</div>
                        <div class='kpi-val' style='font-size:1.8rem; color:#F59E0B;'>{daily_carbs:.1f}g</div>
                    </div>
                    <div>
                        <div class='kpi-lbl'>Fat</div>
                        <div class='kpi-val' style='font-size:1.8rem; color:#EF4444;'>{daily_fat:.1f}g</div>
                    </div>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        # Logged meals list
        st.subheader("Today's Logged Meals")
        if meals:
            for m in meals:
                with st.expander(f"🍴 {m.meal_type.upper()} — {m.meal_date}", expanded=True):
                    entries = nutrition_service.get_meal_entries(m.meal_id)

                    if entries:
                        # Show food items table
                        for entry in entries:
                            food = nutrition_service.get_food_item(entry.food_id)
                            food_name = food.name if food else "Unknown Food"

                            # calculate entry scaling
                            serving = food.serving_size_g if food else 100.0
                            scale = entry.quantity_g / serving
                            entry_cals = (food.calories * scale) if food else 0

                            col_n, col_q, col_c, col_d = st.columns([4, 2, 2, 1])
                            col_n.write(f"**{food_name}**")
                            col_q.write(f"{entry.quantity_g:.0f}g")
                            col_c.write(f"{entry_cals:.0f} kcal")

                            # Delete entry
                            if col_d.button("🗑️", key=f"del_ent_{entry.entry_id}"):
                                try:
                                    nutrition_service.remove_food_from_meal(entry.entry_id)
                                    # Save log recalculation
                                    nutrition_service.save_daily_nutrition_log(
                                        f"nl-{uuid.uuid4().hex[:8]}", user_id, selected_date
                                    )
                                    st.success("Entry removed!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to remove: {e}")
                    else:
                        st.caption("No food items added to this meal yet.")

                    # Form to add food to this meal
                    st.divider()
                    st.markdown("**Add Food Item to Meal**")
                    foods = nutrition_service.list_food_database()
                    if foods:
                        food_options = {
                            f.food_id: f"{f.name} ({f.calories:.0f}kcal / {f.serving_size_g:.0f}g)" for f in foods
                        }
                        selected_food_id = st.selectbox(
                            "Select Food",
                            options=list(food_options.keys()),
                            key=f"sel_food_{m.meal_id}",
                            format_func=lambda x, fo=food_options: fo[x],
                        )
                        qty = st.number_input(
                            "Quantity (grams)", min_value=1.0, value=100.0, step=10.0, key=f"qty_{m.meal_id}"
                        )
                        if st.button("Add to Meal", key=f"btn_add_{m.meal_id}"):
                            try:
                                new_entry = MealEntry(
                                    entry_id=f"ent-{uuid.uuid4().hex[:8]}",
                                    meal_id=m.meal_id,
                                    food_id=selected_food_id,
                                    quantity_g=qty,
                                )
                                nutrition_service.add_food_to_meal(new_entry)
                                # Save daily log calculation
                                nutrition_service.save_daily_nutrition_log(
                                    f"nl-{uuid.uuid4().hex[:8]}", user_id, selected_date
                                )
                                st.success("Food added successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to add food: {e}")
                    else:
                        st.warning("No foods in database. Go to 'Food Database' tab to register one.")

                    # Delete full meal
                    if st.button("Delete Entire Meal", key=f"del_meal_{m.meal_id}", use_container_width=True):
                        try:
                            nutrition_service.delete_meal(m.meal_id)
                            # Save log recalculation
                            nutrition_service.save_daily_nutrition_log(
                                f"nl-{uuid.uuid4().hex[:8]}", user_id, selected_date
                            )
                            st.success("Meal deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete meal: {e}")
        else:
            st.info("No meals logged for today.")

        # Log new meal form
        st.divider()
        st.subheader("Log a New Meal")
        selected_meal_type = st.selectbox("Meal Type", MealType.ALL)
        if st.button("Create Meal Event"):
            try:
                # Ensure user doesn't log duplicate meal type per date
                existing = nutrition_service.meal_repo.get_meal_by_type_and_date(
                    user_id, selected_meal_type, selected_date
                )
                if existing:
                    st.warning(f"You have already created a '{selected_meal_type}' meal event for this date.")
                else:
                    new_meal = Meal(
                        meal_id=f"meal-{uuid.uuid4().hex[:8]}",
                        user_id=user_id,
                        meal_type=selected_meal_type,
                        meal_date=selected_date,
                    )
                    nutrition_service.create_meal(new_meal)
                    st.success(f"{selected_meal_type.upper()} meal event created!")
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to log meal: {e}")

    # --- TAB 2: Food Database ---
    with tab_food_db:
        st.subheader("Food Item Database Library")
        foods = nutrition_service.list_food_database()

        if foods:
            for f in foods:
                st.markdown(
                    f"""
                    <div class='glass-card'>
                        <h4 style='margin:0; color:#818CF8;'>{f.name}</h4>
                        <p style='margin:0; font-size:0.85rem; color:#94a3b8;'>
                            {f.calories:.0f} kcal per {f.serving_size_g:.0f}g | P: {f.protein:.1f}g | C: {f.carbs:.1f}g | F: {f.fats:.1f}g
                        </p>
                    </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Food catalog database is currently empty.")

        st.divider()
        st.subheader("Add Food Item to Library catalog")
        with st.form(key="add_food_form"):
            f_name = st.text_input("Name (e.g. Eggs)")
            f_cals = st.number_input("Calories (kcal per serving)", min_value=0.0, value=155.0)
            f_protein = st.number_input("Protein (grams per serving)", min_value=0.0, value=13.0)
            f_carbs = st.number_input("Carbohydrates (grams per serving)", min_value=0.0, value=1.1)
            f_fats = st.number_input("Fats (grams per serving)", min_value=0.0, value=11.0)
            f_serving = st.number_input("Serving Size (grams)", min_value=1.0, value=100.0)

            f_submit = st.form_submit_button("Register Food Item")
            if f_submit:
                try:
                    new_food = FoodItem(
                        food_id=f"food-{uuid.uuid4().hex[:8]}",
                        name=f_name,
                        calories=f_cals,
                        protein=f_protein,
                        carbs=f_carbs,
                        fats=f_fats,
                        serving_size_g=f_serving,
                    )
                    nutrition_service.add_food_item(new_food)
                    st.success(f"Added {f_name} to database library!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save food: {e}")
