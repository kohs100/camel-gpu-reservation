const submitForm = async () => {
  const form = document.getElementById("gpuForm");

  const username = form.username.value;
  const password = form.password.value;
  const reserved_time = form.reserved_time.value;

  const selectedGPUs = [];
  const gpuCheckboxes = document.querySelectorAll('input[name="gpus"]:checked');
  gpuCheckboxes.forEach((checkbox) => {
    selectedGPUs.push(checkbox.value);
  });

  const requestData = {
    username: username,
    password: password,
    GPUs: selectedGPUs,
    reservation_time: parseFloat(reserved_time) * 3600,
    privileged: form.privileged.checked,
  };

  const output = document.getElementById("response");
  output.innerHTML = "<p style='color: red;'>Waiting for response...</p>";

  try {
    const resp = await fetch("/api/reserve", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestData),
    });
    const data = await resp.json();
    const msg = data["message"];

    if (resp.ok) {
      const port = data["port"];
      output.innerHTML += `<p style='color: green;'>${msg}</p>`;
      output.innerHTML += `<p style='color: green;'>Login with [ssh root@143.248.39.4 -p ${port}] and use your password to login.</p>`;
    } else {
      output.innerHTML += `<p style='color: red;'>${msg}</p>`;
    }
  } catch (err) {
    output.innerHTML += `<p style='color: red;'>AJAX Failed: ${err}</p>`;
  }
  loadStatus();
};

const release = async () => {
  const form = document.getElementById("gpuForm");

  const username = form.username.value;
  const password = form.password.value;

  const requestData = {
    username: username,
    password: password,
  };

  const output = document.getElementById("response");
  output.innerHTML = "<p style='color: red;'>Waiting for response...</p>";

  try {
    const resp = await fetch("/api/release", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestData),
    });
    const data = await resp.json();
    const msg = data["message"];

    if (resp.ok) {
      output.innerHTML += `<p style='color: green;'>${msg}</p>`;
      output.innerHTML += `<p style='color: green;'>Successfully released.</p>`;
    } else {
      output.innerHTML += `<p style='color: red;'>${msg}</p>`;
    }
  } catch (err) {
    output.innerHTML += `<p style='color: red;'>AJAX Failed: ${err}</p>`;
  }
  loadStatus();
};

const extend = async() => {
  const form = document.getElementById("gpuForm");

  const username = form.username.value;
  const password = form.password.value;
  const reserved_time = form.reserved_time.value;

  const requestData = {
    username: username,
    password: password,
    reservation_time: parseFloat(reserved_time) * 3600,
  };

  const output = document.getElementById("response");
  output.innerHTML = "<p style='color: red;'>Waiting for response...</p>";

  try {
    const resp = await fetch("/api/extend", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestData),
    });
    const data = await resp.json();
    const msg = data["message"];

    if (resp.ok) {
      output.innerHTML += `<p style='color: green;'>${msg}</p>`;
      output.innerHTML += `<p style='color: green;'>Successfully extended.</p>`;
    } else {
      output.innerHTML += `<p style='color: red;'>${msg}</p>`;
    }
  } catch (err) {
    output.innerHTML += `<p style='color: red;'>AJAX Failed: ${err}</p>`;
  }
  loadStatus();
}

const check = async () => {
  const form = document.getElementById("gpuForm");

  const username = form.username.value;
  const password = form.password.value;

  const requestData = {
    username: username,
    password: password,
  };

  const output = document.getElementById("response");
  output.innerHTML = "<p style='color: red;'>Waiting for response...</p>";

  try {
    const resp = await fetch("/api/userstatus", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestData),
    });

    const data = await resp.json();

    const msg = data["message"];
    const created = data["created"];
    const running = data["running"];
    const imaged = data["imaged"];
    const port = data["port"];

    if (resp.ok) {
      if (running) {
        output.innerHTML += `<p style='color: green;'>Login with [ssh root@143.248.39.4 -p ${port}] and use your password to login.</p>`;
      } else if (created) {
        output.innerHTML += `<p style='color: green;'>Container is not running but is created.</p>`;
      } else if (imaged) {
        output.innerHTML += `<p style='color: green;'>Container is not created but image is persisted.</p>`;
      } else {
        output.innerHTML += `<p style='color: red;'>No container information exists.</p>`;
      }
    } else {
      output.innerHTML += `<p style='color: red;'>${msg}</p>`;
    }
  } catch (err) {
    output.innerHTML += `<p style='color: red;'>AJAX Failed: ${err}</p>`;
  }
  loadStatus();
};

const loadStatus = async () => {
  const response = await fetch("/api/status", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache, no-store, max-age=0",
    },
  });
  const data = await response.json();
  const gpu_status = data["gpu_status"];
  const currentTime = Date.now() / 1000;

  let innerHTML = "";

  Object.entries(gpu_status).map(([key, value]) => {
    if (value["invalid_until"] > currentTime) {
      innerHTML += `<input type="checkbox" disabled id="${key}" name="gpus" value="${key}">`;
      innerHTML += `<label for="${key}">${key} (Reserved by ${
        value["user"]
      } until ${new Date(
        value["invalid_until"] * 1000
      ).toLocaleString()})</label><br>`;
    } else {
      innerHTML += `<input type="checkbox" id="${key}" name="gpus" value="${key}">`;
      innerHTML += `<label for="${key}">${key}</label><br>`;
    }
  });

  document.getElementById("available_gpus").innerHTML = innerHTML;
};
loadStatus();
