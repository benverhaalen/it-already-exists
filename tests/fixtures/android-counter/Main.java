package org.rdd.fixture;

import android.app.Activity;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Owned harmless reference: persistent state, delayed effect and native UI. */
public class Main extends Activity {
    private SharedPreferences preferences;
    private TextView value;
    private int count;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        preferences = getSharedPreferences("fixture", MODE_PRIVATE);
        count = preferences.getInt("count", 0);
        preferences.edit().putInt("count", count).commit();
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(40, 120, 40, 40);
        TextView title = new TextView(this);
        title.setText("Reference counter");
        title.setTextSize(28);
        content.addView(title);
        value = new TextView(this);
        value.setTextSize(40);
        value.setContentDescription("Persistent count");
        value.setText(String.valueOf(count));
        content.addView(value);
        final Button increment = new Button(this);
        increment.setText("Increment");
        increment.setContentDescription("Increment persistent count");
        increment.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View view) {
                increment.setEnabled(false);
                new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                    @Override public void run() {
                        count++;
                        preferences.edit().putInt("count", count).commit();
                        value.setText(String.valueOf(count));
                        increment.setEnabled(true);
                    }
                }, 200);
            }
        });
        content.addView(increment);
        setContentView(content);
    }
}
