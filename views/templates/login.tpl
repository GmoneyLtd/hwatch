<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hwatch - Play Login</title>
    <link rel="stylesheet" href="/static/css/app.css">
</head>

<body>
    <header class="login-header">
        <div class="container">
            <h1>Hwatch</h1>
        </div>
    </header>

    <main>
        <div class="login-container">
            <div class="login-box">
                <h2>
                    <span class="material-symbols-outlined login-icon" aria-hidden="true">manage_accounts</span>
                    Admin Login
                </h2>

                {% if error %}
                <div class="error-message">
                    {{ error }}
                </div>
                {% endif %}

                <form action="/login" method="post" class="login-form">
                    <div class="form-group">
                        <label for="username">User</label>
                        <input type="text" id="username" name="username" required>
                    </div>

                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>

                    <button type="submit" class="btn btn-upload">Login</button>
                </form>
            </div>
        </div>
    </main>
</body>

</html>