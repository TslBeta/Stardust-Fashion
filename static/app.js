const view = document.getElementById('view');
const toastNode = document.getElementById('toast');
const state = { token: localStorage.getItem('stardust_token') || '', user: null, cart: null, product: null, variantId: null, adminTab: 'orders', adminProductId: null, page: 1 };
const money = n => new Intl.NumberFormat('vi-VN').format(n || 0) + ' ₫';
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const statusText = {PENDING:'Chờ xử lý',CONFIRMED:'Đã xác nhận',SHIPPING:'Đang giao',COMPLETED:'Hoàn thành',CANCELLED:'Đã hủy',SUCCESS:'Thành công',FAILED:'Thất bại',UNPAID:'Chưa thanh toán'};

function toast(message, error=false){toastNode.textContent=message;toastNode.className='toast show'+(error?' error':'');clearTimeout(toast.timer);toast.timer=setTimeout(()=>toastNode.className='toast',4500)}
async function api(path, options={}){
  const headers = {'Content-Type':'application/json',...options.headers};
  if(state.token) headers.Authorization = 'Bearer '+state.token;
  const response = await fetch('/api/v1'+path,{...options,headers});
  if(response.status===204) return null;
  let body; try{body=await response.json()}catch{throw new Error('Máy chủ không trả JSON hợp lệ.')}
  if(!response.ok){const error=new Error(body.error?.message || 'Yêu cầu không thành công.');error.status=response.status;throw error}
  return body;
}
const post=(path,data)=>api(path,{method:'POST',body:JSON.stringify(data)});
const patch=(path,data)=>api(path,{method:'PATCH',body:JSON.stringify(data)});
const del=path=>api(path,{method:'DELETE'});
function field(label,name,type='text',value='',required=true,extra=''){
  return `<div class="field"><label for="${name}">${label}</label><input id="${name}" name="${name}" type="${type}" value="${escapeHtml(value)}" ${required?'required':''} ${extra}></div>`;
}
function status(s){return `<span class="status ${escapeHtml(s)}">${escapeHtml(statusText[s]||s)}</span>`}
function setView(html){view.innerHTML=html;window.scrollTo(0,0)}
function route(){const raw=(location.hash||'#home').slice(1);return {name:raw.split('?')[0]||'home',query:new URLSearchParams(raw.split('?')[1]||'')}}
async function refreshHeader(){
  if(state.token){try{state.user=await api('/me');state.cart=state.user.role==='CUSTOMER'?await api('/cart'):null}catch(error){if(error.status===401){state.token='';state.user=null;state.cart=null;localStorage.removeItem('stardust_token')}else toast(error.message,true)}}
  document.querySelectorAll('.signed-only').forEach(el=>el.style.display=state.user?.role==='CUSTOMER'?'inline':'none');
  document.querySelectorAll('.admin-only').forEach(el=>el.style.display=state.user?.role==='ADMIN'?'inline':'none');
  document.getElementById('account-link').textContent=state.user?state.user.full_name:'TÀI KHOẢN';
  document.getElementById('cart-count').textContent=state.cart?.items?.reduce((n,x)=>n+x.quantity,0)||0;
}
async function navigate(){
  const {name,query}=route();
  try{
    if(name==='home') return home();
    if(name==='shop') return await shop();
    if(name.startsWith('product/')) return await product(name.split('/')[1]);
    if(name==='cart') return await cart();
    if(name==='checkout') return await checkout();
    if(name==='login'||name==='register'||name==='forgot'||name==='reset') return authScreen(name);
    if(name==='account') return await account();
    if(name==='orders') return await orders(query);
    if(name==='admin') return await admin();
    location.hash='#home';
  }catch(error){setView(`<div class="view-pad"><h1 class="headline view-title">KHÔNG TẢI ĐƯỢC</h1><p>${escapeHtml(error.message)}</p><a class="button" href="#home">VỀ TRANG CHỦ</a></div>`);toast(error.message,true)}
}
const heroProducts=[
  {id:1,name:'NEBULA OVERSIZED TEE',price:150000,image_url:'/static/images/tee.png'},
  {id:2,name:'ORBIT HOODIE',price:390000,image_url:'/static/images/hero.png'},
  {id:3,name:'SOLAR RELAXED TEE',price:190000,image_url:'/static/images/cream-tee.png'},
  {id:4,name:'DRIFT CARGO PANTS',price:250000,image_url:'/static/images/pants.png'},
  {id:5,name:'VOID CAP',price:120000,image_url:'/static/images/cap.png'}
];
function productCard(p){return `<a class="product-card" href="#product/${p.id}"><div class="photo"><img loading="lazy" src="${escapeHtml(p.image_url||'/static/images/tee.png')}" alt="${escapeHtml(p.name)}"></div><div class="product-card-info"><strong>${escapeHtml(p.name)}</strong><span>${money(p.price)}</span></div></a>`}
function home(){
  setView(`<section class="hero"><div class="hero-meta"><span>STARDUST FASHION<br>EST. 2026</span><span>NEW SEASON / 01</span></div><h1 class="headline">SHOP SMARTER.<br>LIVE BRIGHTER<br>WITH STARDUST.</h1><img class="hero-img one" src="/static/images/cream-tee.png" alt="Áo thun sáng màu"><img class="hero-img two" src="/static/images/hero.png" alt="Hoodie đen Stardust"><img class="hero-img three" src="/static/images/cap.png" alt="Mũ đen Stardust"><p class="hero-copy">MADE FOR THE STREETS. DESIGNED FOR YOUR EVERYDAY ORBIT.</p><p class="hero-side">OUR LATEST COLLECTION IS MADE TO MAKE A STATEMENT.</p><div class="hero-bottom"><a class="button" href="#shop">SHOP NOW ↗</a><span>01 / 2026<br>SCROLL TO EXPLORE ↓</span></div></section>
  <section class="feature"><img class="feature-photo" src="/static/images/cream-tee.png" alt="Áo thun cotton Stardust"><div class="feature-content"><span class="eyebrow">OUR QUALITY / EVERYDAY FORM</span><h2 class="headline">PREMIUM COTTON. RELAXED FIT. LIMITLESS STYLE.</h2><a class="button" href="#product/3">KHÁM PHÁ SẢN PHẨM</a></div></section>
  <section class="collection"><div class="collection-top"><span class="eyebrow">DROP 01 — THE CITY COLLECTION</span><h2>Stardust</h2></div><div class="product-grid">${heroProducts.slice(0,4).map(productCard).join('')}</div><div class="center-cta"><a class="button" href="#shop">XEM TẤT CẢ SẢN PHẨM</a></div></section>
  <section class="campaign"><div><img src="/static/images/pants.png" alt="Cargo pants"><p>BUILT TO MOVE WITH YOU.</p></div><div><h2 class="headline">WHETHER YOU'RE HITTING THE STREETS OR CHILLING WITH FRIENDS.</h2><a class="button" href="#shop">BUILD YOUR LOOK</a></div><div><img src="/static/images/tee.png" alt="Oversized tee"><p>YOUR STYLE. YOUR UNIVERSE.</p></div></section>`);
}
async function shop(){
  const categories=await api('/categories');const p=new URLSearchParams(location.hash.split('?')[1]||'');const page=Number(p.get('page')||1);
  const params=new URLSearchParams();['search','categoryId','minPrice','maxPrice'].forEach(k=>{if(p.get(k))params.set(k,p.get(k))});params.set('page',String(page));params.set('limit','12');
  const result=await api('/products?'+params);
  setView(`<section class="view-pad"><div class="split-head"><div><span class="eyebrow">STARDUST FASHION / COLLECTION</span><h1 class="headline view-title">SHOP THE<br>UNIVERSE.</h1></div><span class="eyebrow">${result.total} SẢN PHẨM</span></div><form id="shop-form" class="shop-controls"><input name="search" aria-label="Tìm theo tên" placeholder="TÌM THEO TÊN" value="${escapeHtml(p.get('search')||'')}"><select name="categoryId" aria-label="Danh mục"><option value="">TẤT CẢ DANH MỤC</option>${categories.map(c=>`<option value="${c.id}" ${p.get('categoryId')==c.id?'selected':''}>${escapeHtml(c.name)}</option>`).join('')}</select><input type="number" name="minPrice" min="0" placeholder="GIÁ TỪ" aria-label="Giá từ" value="${escapeHtml(p.get('minPrice')||'')}"><input type="number" name="maxPrice" min="0" placeholder="GIÁ ĐẾN" aria-label="Giá đến" value="${escapeHtml(p.get('maxPrice')||'')}"><button class="button" type="submit">LỌC ↗</button></form>${result.items.length?`<div class="shop-grid">${result.items.map(productCard).join('')}</div>`:'<div class="empty">Không tìm thấy sản phẩm phù hợp.</div>'}<div class="pagination"><button class="button outline small" data-action="shop-page" data-page="${page-1}" ${page<=1?'disabled':''}>← TRƯỚC</button><span>${page} / ${Math.max(1,Math.ceil(result.total/result.limit))}</span><button class="button outline small" data-action="shop-page" data-page="${page+1}" ${page*result.limit>=result.total?'disabled':''}>TIẾP →</button></div></section>`);
}
async function product(id){
  const p=await api('/products/'+id);state.product=p;state.variantId=p.variants.find(v=>v.stock>0)?.id||null;
  setView(`<div class="product-layout"><img src="${escapeHtml(p.image_url)}" alt="${escapeHtml(p.name)}"><div class="product-info"><div class="breadcrumb"><a href="#shop">SHOP</a> / ${escapeHtml(p.category_name)} / ${escapeHtml(p.name)}</div><h1 class="headline">${escapeHtml(p.name)}</h1><p class="price">${money(p.price)}</p><p>${escapeHtml(p.description||'')}</p><div class="rule" style="margin:28px 0"></div><span class="eyebrow">CHỌN SIZE / MÀU</span><div class="variant-list">${p.variants.map(v=>`<button class="variant ${v.id===state.variantId?'selected':''}" data-action="variant" data-id="${v.id}" ${v.stock<1?'disabled':''}>${escapeHtml(v.size)} / ${escapeHtml(v.color)}${v.stock<1?' · HẾT HÀNG':''}</button>`).join('')}</div><div id="stock-note" class="muted">${state.variantId?'Còn '+p.variants.find(v=>v.id===state.variantId).stock+' sản phẩm':'Hiện hết hàng'}</div><div class="qty-row"><span class="eyebrow">SỐ LƯỢNG</span><input id="product-quantity" type="number" min="1" max="99" value="1"></div><button class="button" data-action="add-cart" ${!state.variantId?'disabled':''}>THÊM VÀO GIỎ →</button><p class="muted">Giá tính lại khi đặt hàng. Phí giao hàng 30.000 ₫/đơn.</p></div></div>`);
}
async function cart(){
  if(!state.user){location.hash='#login';return}if(state.user.role!=='CUSTOMER'){location.hash='#admin';return}
  state.cart=await api('/cart');await refreshHeader();const items=state.cart.items;
  setView(`<section class="view-pad"><span class="eyebrow">YOUR EDIT / YOUR ORBIT</span><h1 class="headline view-title">GIỎ HÀNG.</h1>${items.length?`<div class="two-col"><div class="panel">${items.map(x=>`<div class="cart-line"><img src="${escapeHtml(x.image_url)}" alt="${escapeHtml(x.product_name)}"><div><h3>${escapeHtml(x.product_name)}</h3><div class="muted">${escapeHtml(x.size)} / ${escapeHtml(x.color)}</div><div style="margin-top:12px"><input aria-label="Số lượng" type="number" min="1" max="99" value="${x.quantity}" data-quantity-for="${x.id}"> <button class="link-btn" data-action="update-cart" data-id="${x.id}">Cập nhật</button> · <button class="link-btn" data-action="delete-cart" data-id="${x.id}">Xóa</button></div>${!x.available?`<p style="color:#b22">${escapeHtml(x.unavailable_reason||'Mặt hàng không còn đủ điều kiện mua.')}</p>`:''}</div><strong>${money(x.line_total)}</strong></div>`).join('')}</div><div class="panel"><span class="eyebrow">TÓM TẮT ĐƠN HÀNG</span><div class="summary-row"><span>Tiền hàng</span><strong>${money(state.cart.subtotal)}</strong></div><div class="summary-row"><span>Phí vận chuyển</span><strong>${money(state.cart.shipping_fee)}</strong></div><div class="summary-row total"><span>Tổng dự kiến</span><span>${money(state.cart.subtotal+state.cart.shipping_fee)}</span></div><a class="button" style="width:100%;margin-top:20px" href="#checkout">TIẾN HÀNH ĐẶT HÀNG →</a></div></div>`:'<div class="empty"><p>Giỏ hàng đang rỗng.</p><a class="button" href="#shop">KHÁM PHÁ SẢN PHẨM</a></div>'}</section>`);
}
async function checkout(){
  if(!state.user){location.hash='#login';return}if(state.user.role!=='CUSTOMER'){location.hash='#admin';return}
  const c=await api('/cart');if(!c.items.length){location.hash='#cart';return}
  setView(`<section class="view-pad"><span class="eyebrow">FINAL STEP / CHECKOUT</span><h1 class="headline view-title">ĐẶT HÀNG.</h1><div class="two-col"><form id="checkout-form" class="panel stack">${field('Người nhận','recipient_name','text',state.user.full_name,true,'minlength="2" maxlength="100"')}${field('Số điện thoại','recipient_phone','tel',state.user.phone||'',true,'pattern="0[0-9]{9}"')}${field('Địa chỉ nhận hàng','address','text','',true,'minlength="10" maxlength="255"')}<div class="field"><label for="payment_method">Thanh toán</label><select id="payment_method" name="payment_method"><option value="COD">Thanh toán khi nhận hàng (COD)</option><option value="ONLINE">MoMo sandbox</option></select></div><button class="button" type="submit">XÁC NHẬN ĐẶT HÀNG →</button><p class="muted">MoMo cần khóa sandbox và IPN URL công khai. Đơn COD có thể thử ngay sau khi cài MySQL.</p></form><div class="panel"><span class="eyebrow">ĐƠN CỦA BẠN</span>${c.items.map(x=>`<div class="summary-row"><span>${escapeHtml(x.product_name)} × ${x.quantity}</span><strong>${money(x.line_total)}</strong></div>`).join('')}<div class="summary-row"><span>Phí vận chuyển</span><strong>${money(30000)}</strong></div><div class="summary-row total"><span>Tổng tiền</span><span>${money(c.subtotal+30000)}</span></div></div></div></section>`);
}
function authScreen(name){
  const titles={login:'ĐĂNG NHẬP.',register:'ĐĂNG KÝ.',forgot:'QUÊN MẬT KHẨU.',reset:'ĐẶT LẠI MẬT KHẨU.'};
  let body='';
  if(name==='login')body=field('Email','email','email')+field('Mật khẩu','password','password')+'<button class="button">ĐĂNG NHẬP</button><div class="form-links"><a href="#register">Tạo tài khoản</a><a href="#forgot">Quên mật khẩu?</a></div>';
  if(name==='register')body=field('Họ và tên','full_name')+field('Email','email','email')+field('Số điện thoại','phone','tel','',false)+field('Mật khẩu (8–64 ký tự, chữ và số)','password','password')+'<button class="button">TẠO TÀI KHOẢN</button><div class="form-links"><a href="#login">Đã có tài khoản?</a></div>';
  if(name==='forgot')body=field('Email','email','email')+'<button class="button">TẠO MÃ ĐẶT LẠI</button><p class="muted">Ở môi trường development, mã đặt lại hiển thị sau khi gửi. Hệ thống không gửi email thật.</p>';
  if(name==='reset')body=field('Mã đặt lại','reset_token')+field('Mật khẩu mới','new_password','password')+'<button class="button">ĐẶT LẠI MẬT KHẨU</button>';
  setView(`<section class="view-pad"><form id="${name}-form" class="form-card"><span class="eyebrow">STARDUST / ACCOUNT</span><h1 class="headline">${titles[name]}</h1>${body}</form></section>`);
}
async function account(){
  if(!state.user){location.hash='#login';return}
  setView(`<section class="view-pad"><span class="eyebrow">HELLO, ${escapeHtml(state.user.full_name)}</span><h1 class="headline view-title">TÀI KHOẢN.</h1><div class="account-grid"><form id="profile-form" class="panel stack"><h2>Hồ sơ cá nhân</h2><p>Email: ${escapeHtml(state.user.email)} · Vai trò: ${escapeHtml(state.user.role)}</p>${field('Họ và tên','full_name','text',state.user.full_name)}${field('Số điện thoại','phone','tel',state.user.phone||'',false)}<button class="button" type="submit">LƯU HỒ SƠ</button></form><form id="password-form" class="panel stack"><h2>Đổi mật khẩu</h2>${field('Mật khẩu hiện tại','current_password','password')}${field('Mật khẩu mới','new_password','password')}<button class="button" type="submit">ĐỔI MẬT KHẨU</button></form></div><button class="button dark" data-action="logout" style="margin-top:24px">ĐĂNG XUẤT</button></section>`);
}
function orderCard(o,admin=false){
  const actions=[];
  if(!admin&&o.status==='PENDING')actions.push(`<button class="button outline small" data-action="cancel-order" data-id="${o.id}">HỦY ĐƠN</button>`);
  if(!admin&&o.payment_method==='ONLINE'&&o.status==='PENDING'&&o.payment_status!=='SUCCESS')actions.push(`<button class="button small" data-action="pay-momo" data-id="${o.id}">THANH TOÁN MOMO</button>`);
  if(admin){const choices={PENDING:['CONFIRMED','CANCELLED'],CONFIRMED:['SHIPPING','CANCELLED'],SHIPPING:['COMPLETED']}[o.status]||[];for(const s of choices)actions.push(`<button class="button small" data-action="admin-status" data-id="${o.id}" data-status="${s}">${statusText[s].toUpperCase()}</button>`)}
  return `<div class="order-card"><div class="order-top"><h3>ĐƠN #${o.id}</h3>${status(o.status)}</div><div class="order-meta"><span>${escapeHtml(o.created_at||'')}</span><span>${admin?escapeHtml(o.email||''):''}</span><span>${o.payment_method==='COD'?'COD':'MOMO'} / ${status(o.payment_status)}</span><strong>${money(o.total)}</strong></div><div class="order-items">${o.items?o.items.map(x=>`<div class="summary-row"><span>${escapeHtml(x.product_name)} · ${escapeHtml(x.size)} / ${escapeHtml(x.color)} × ${x.quantity}</span><strong>${money(x.line_total)}</strong></div>`).join(''):`<button class="link-btn" data-action="order-detail" data-id="${o.id}" data-admin="${admin?'1':'0'}">Xem chi tiết</button>`}</div><div class="order-actions">${actions.join('')}</div></div>`;
}
async function orders(query){
  if(!state.user){location.hash='#login';return}if(state.user.role!=='CUSTOMER'){location.hash='#admin';return}
  const list=await api('/orders');setView(`<section class="view-pad"><span class="eyebrow">TRACK YOUR ORBIT</span><h1 class="headline view-title">ĐƠN HÀNG.</h1>${list.length?list.map(x=>orderCard(x)).join(''):'<div class="empty"><p>Bạn chưa có đơn hàng.</p><a class="button" href="#shop">MUA SẮM NGAY</a></div>'}</section>`);
  if(query.get('payment'))toast('Kết quả MoMo: '+(statusText[query.get('payment').toUpperCase()]||query.get('payment')));
}
async function admin(){
  if(!state.user){location.hash='#login';return}if(state.user.role!=='ADMIN'){location.hash='#home';return}
  const tabs=['orders','categories','products'];const labels={orders:'ĐƠN HÀNG',categories:'DANH MỤC',products:'SẢN PHẨM & KHO'};
  let body='';
  if(state.adminTab==='orders'){
    const list=await api('/admin/orders');body=`<div class="field" style="max-width:250px;margin-bottom:20px"><label>Lọc trạng thái</label><select id="admin-order-filter"><option value="">TẤT CẢ</option>${['PENDING','CONFIRMED','SHIPPING','COMPLETED','CANCELLED'].map(s=>`<option value="${s}">${statusText[s]}</option>`).join('')}</select></div><div id="admin-orders-list">${list.length?list.map(x=>orderCard(x,true)).join(''):'<div class="empty">Chưa có đơn hàng.</div>'}</div>`;
  }
  if(state.adminTab==='categories'){
    const rows=await api('/admin/categories');body=`<form id="category-form" class="admin-form">${field('Tên danh mục','name')}<div class="field"><label for="category-active">Trạng thái</label><select id="category-active" name="active"><option value="true">Hoạt động</option><option value="false">Ngừng</option></select></div><button class="button">THÊM DANH MỤC</button></form><div class="admin-list">${rows.map(c=>`<div class="admin-item"><div><strong>#${c.id} ${escapeHtml(c.name)}</strong> · ${c.active?'Đang hoạt động':'Đã ngừng'}</div><div class="actions"><button class="button outline small" data-action="rename-category" data-id="${c.id}" data-name="${escapeHtml(c.name)}">ĐỔI TÊN</button><button class="button outline small" data-action="toggle-category" data-id="${c.id}" data-active="${c.active}">${c.active?'NGỪNG':'MỞ'} BÁN</button><button class="button outline small" data-action="delete-category" data-id="${c.id}">XÓA</button></div></div>`).join('')}</div>`;
  }
  if(state.adminTab==='products'){
    const [rows,categories]=await Promise.all([api('/admin/products'),api('/admin/categories')]);
    body=`<form id="new-product-form" class="admin-form"><div class="field"><label for="category_id">Danh mục</label><select id="category_id" name="category_id">${categories.map(c=>`<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('')}</select></div>${field('Tên sản phẩm','name')}${field('Giá VND','price','number','','true','min="1" max="100000000"')}${field('Đường dẫn ảnh','image_url','text','',false)}<div class="field wide"><label for="description">Mô tả</label><input id="description" name="description" maxlength="5000"></div><button class="button">TẠO SẢN PHẨM</button></form><p class="muted">Sản phẩm mới ngừng bán. Thêm biến thể rồi mở bán.</p><div class="admin-list">${rows.map(p=>`<div class="admin-item"><div><strong>#${p.id} ${escapeHtml(p.name)}</strong><br><span class="muted">${escapeHtml(p.category_name)} · ${money(p.price)} · ${p.active?'Đang bán':'Ngừng bán'}</span></div><div class="actions"><button class="button outline small" data-action="edit-product" data-id="${p.id}">SỬA</button><button class="button outline small" data-action="toggle-product" data-id="${p.id}" data-active="${p.active}">${p.active?'NGỪNG':'MỞ'} BÁN</button><button class="button dark small" data-action="manage-variants" data-id="${p.id}">BIẾN THỂ / KHO</button></div></div>`).join('')}</div><div id="variant-panel"></div>`;
  }
  setView(`<section class="view-pad"><span class="eyebrow">STARDUST / BACK OFFICE</span><h1 class="headline view-title">QUẢN TRỊ.</h1><div class="admin-tabs">${tabs.map(t=>`<button data-action="admin-tab" data-tab="${t}" class="${state.adminTab===t?'active':''}">${labels[t]}</button>`).join('')}</div>${body}</section>`);
  if(state.adminProductId&&state.adminTab==='products')await showVariants(state.adminProductId);
}
async function showVariants(id){
  const p=await api('/admin/products/'+id);state.adminProductId=id;const panel=document.getElementById('variant-panel');if(!panel)return;
  panel.innerHTML=`<div class="panel" style="margin-top:28px"><h2>Biến thể: ${escapeHtml(p.name)}</h2><form id="variant-form" class="admin-form">${field('Size','size')}${field('Màu','color')}${field('Tồn kho','stock','number','0',true,'min="0" max="100000"')}<button class="button">THÊM BIẾN THỂ</button></form><div class="admin-list">${p.variants.map(v=>`<div class="admin-item"><div><strong>#${v.id} ${escapeHtml(v.size)} / ${escapeHtml(v.color)}</strong><br><span class="muted">${v.active?'Đang bán':'Ngừng bán'} · Tồn ${v.stock}</span></div><div class="actions"><input aria-label="Tồn kho biến thể ${v.id}" type="number" min="0" max="100000" value="${v.stock}" data-stock-for="${v.id}"><button class="button outline small" data-action="save-stock" data-id="${v.id}">LƯU KHO</button><button class="button outline small" data-action="toggle-variant" data-id="${v.id}" data-active="${v.active}">${v.active?'NGỪNG':'MỞ'} BÁN</button></div></div>`).join('')}</div></div>`;panel.scrollIntoView({behavior:'smooth'});
}
async function action(button){
  const a=button.dataset.action,id=Number(button.dataset.id);
  if(a==='variant'){state.variantId=id;document.querySelectorAll('.variant').forEach(x=>x.classList.toggle('selected',Number(x.dataset.id)===id));const v=state.product.variants.find(x=>x.id===id);document.getElementById('stock-note').textContent='Còn '+v.stock+' sản phẩm';return}
  if(a==='add-cart'){if(!state.user){location.hash='#login';return}await post('/cart/items',{variant_id:state.variantId,quantity:Number(document.getElementById('product-quantity').value)});await refreshHeader();toast('Đã thêm vào giỏ hàng.');return}
  if(a==='shop-page'){const p=new URLSearchParams(location.hash.split('?')[1]||'');p.set('page',button.dataset.page);location.hash='#shop?'+p;return}
  if(a==='update-cart'){await patch('/cart/items/'+id,{quantity:Number(document.querySelector(`[data-quantity-for="${id}"]`).value)});toast('Đã cập nhật giỏ hàng.');return cart()}
  if(a==='delete-cart'){await del('/cart/items/'+id);toast('Đã xóa sản phẩm.');return cart()}
  if(a==='logout'){await post('/auth/logout',{});state.token='';state.user=null;state.cart=null;localStorage.removeItem('stardust_token');await refreshHeader();location.hash='#home';toast('Đã đăng xuất.');return}
  if(a==='cancel-order'){if(!confirm('Hủy đơn #'+id+'? Tồn kho sẽ được hoàn lại.'))return;await patch('/orders/'+id+'/cancel',{status:'CANCELLED'});toast('Đã hủy đơn hàng.');return orders(new URLSearchParams())}
  if(a==='pay-momo'){const result=await post('/orders/'+id+'/payments/momo',{});location.href=result.payment_url;return}
  if(a==='order-detail'){const data=await api((button.dataset.admin==='1'?'/admin/orders/':'/orders/')+id);button.closest('.order-card').outerHTML=orderCard(data,button.dataset.admin==='1');return}
  if(a==='admin-tab'){state.adminTab=button.dataset.tab;state.adminProductId=null;return admin()}
  if(a==='admin-status'){await patch('/admin/orders/'+id+'/status',{status:button.dataset.status});toast('Đã cập nhật trạng thái đơn.');return admin()}
  if(a==='rename-category'){const name=prompt('Tên danh mục mới',button.dataset.name);if(name===null)return;await patch('/admin/categories/'+id,{name});toast('Đã đổi tên danh mục.');return admin()}
  if(a==='toggle-category'){await patch('/admin/categories/'+id,{active:button.dataset.active!=='true'});toast('Đã cập nhật danh mục.');return admin()}
  if(a==='delete-category'){if(!confirm('Xóa danh mục #'+id+'? Chỉ danh mục không có sản phẩm mới được xóa.'))return;await del('/admin/categories/'+id);toast('Đã xóa danh mục.');return admin()}
  if(a==='edit-product'){const p=await api('/admin/products/'+id);const name=prompt('Tên sản phẩm',p.name);if(name===null)return;const price=prompt('Giá VND',p.price);if(price===null)return;const image_url=prompt('Đường dẫn ảnh',p.image_url||'');if(image_url===null)return;const description=prompt('Mô tả',p.description||'');if(description===null)return;await patch('/admin/products/'+id,{name,price:Number(price),image_url,description});toast('Đã sửa sản phẩm.');return admin()}
  if(a==='toggle-product'){await patch('/admin/products/'+id,{active:button.dataset.active!=='true'});toast('Đã cập nhật sản phẩm.');return admin()}
  if(a==='manage-variants')return showVariants(id);
  if(a==='save-stock'){await patch('/admin/variants/'+id,{stock:Number(document.querySelector(`[data-stock-for="${id}"]`).value)});toast('Đã cập nhật kho.');return showVariants(state.adminProductId)}
  if(a==='toggle-variant'){await patch('/admin/variants/'+id,{active:button.dataset.active!=='true'});toast('Đã cập nhật biến thể.');return showVariants(state.adminProductId)}
}
document.addEventListener('click',async event=>{const button=event.target.closest('[data-action]');if(!button)return;try{button.disabled=true;await action(button)}catch(error){toast(error.message,true)}finally{if(button.isConnected)button.disabled=false}});
document.addEventListener('submit',async event=>{
  const form=event.target;if(!form.id)return;event.preventDefault();const data=Object.fromEntries(new FormData(form));
  try{
    if(form.id==='shop-form'){const p=new URLSearchParams();for(const [k,v] of Object.entries(data))if(v)p.set(k,v);location.hash='#shop?'+p;return}
    if(form.id==='login-form'){const result=await post('/auth/login',data);state.token=result.token;localStorage.setItem('stardust_token',result.token);await refreshHeader();location.hash=result.user.role==='ADMIN'?'#admin':'#home';toast('Đăng nhập thành công.');return}
    if(form.id==='register-form'){await post('/auth/register',data);toast('Đã tạo tài khoản. Hãy đăng nhập.');location.hash='#login';return}
    if(form.id==='forgot-form'){const result=await post('/auth/forgot-password',data);if(result.reset_token){toast('Mã đặt lại đã tạo. Đã điền vào biểu mẫu kế tiếp.');location.hash='#reset';setTimeout(()=>{const input=document.getElementById('reset_token');if(input)input.value=result.reset_token},100)}else toast(result.message);return}
    if(form.id==='reset-form'){await post('/auth/reset-password',data);toast('Đã đặt lại mật khẩu.');location.hash='#login';return}
    if(form.id==='profile-form'){await patch('/me',data);await refreshHeader();toast('Đã lưu hồ sơ.');return account()}
    if(form.id==='password-form'){await post('/auth/change-password',data);toast('Đã đổi mật khẩu.');form.reset();return}
    if(form.id==='checkout-form'){const order=await post('/orders',data);await refreshHeader();toast('Đã tạo đơn #'+order.id+'.');if(data.payment_method==='ONLINE'){try{const payment=await post('/orders/'+order.id+'/payments/momo',{});location.href=payment.payment_url;return}catch(error){toast('Đơn đã tạo; MoMo chưa khởi tạo: '+error.message,true)}}location.hash='#orders';return}
    if(form.id==='category-form'){await post('/admin/categories',{name:data.name,active:data.active==='true'});toast('Đã thêm danh mục.');return admin()}
    if(form.id==='new-product-form'){await post('/admin/products',{category_id:Number(data.category_id),name:data.name,price:Number(data.price),description:data.description,image_url:data.image_url});toast('Đã tạo sản phẩm ngừng bán.');return admin()}
    if(form.id==='variant-form'){await post('/admin/products/'+state.adminProductId+'/variants',{size:data.size,color:data.color,stock:Number(data.stock)});toast('Đã thêm biến thể.');return showVariants(state.adminProductId)}
  }catch(error){toast(error.message,true)}
});
document.addEventListener('change',async event=>{if(event.target.id==='admin-order-filter'){try{const statusValue=event.target.value;const list=await api('/admin/orders'+(statusValue?'?status='+statusValue:''));document.getElementById('admin-orders-list').innerHTML=list.length?list.map(x=>orderCard(x,true)).join(''):'<div class="empty">Không có đơn hàng.</div>'}catch(error){toast(error.message,true)}}});
window.addEventListener('hashchange',navigate);
refreshHeader().then(navigate);
